"""
Decal effectiveness evaluation pipeline.

Scores generated decal candidates across multiple OCR engines, simulated
capture conditions (distance, angle, IR, motion blur), and measures
cross-architecture transferability.

Produces ranked results showing which decals are most effective at
corrupting camera reads.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

import numpy as np

try:
    from PIL import Image
except ImportError:
    Image = None


@dataclass
class ConditionSet:
    """A set of capture conditions to evaluate under."""
    name: str
    distance_ft: float = 25.0
    angle_deg: float = 0.0
    motion_blur_px: int = 0
    simulate_ir: bool = False
    ir_wavelength_nm: int = 850


# Standard condition sets representing typical Flock capture scenarios
STANDARD_CONDITIONS = [
    ConditionSet("ideal", distance_ft=20.0),
    ConditionSet("mid_range", distance_ft=35.0),
    ConditionSet("far", distance_ft=50.0),
    ConditionSet("angled", distance_ft=25.0, angle_deg=15.0),
    ConditionSet("motion", distance_ft=25.0, motion_blur_px=8),
    ConditionSet("ir_850nm", distance_ft=25.0, simulate_ir=True, ir_wavelength_nm=850),
    ConditionSet("ir_940nm", distance_ft=25.0, simulate_ir=True, ir_wavelength_nm=940),
    ConditionSet("worst_case", distance_ft=45.0, angle_deg=10.0, motion_blur_px=5),
]


@dataclass
class SingleResult:
    """Result from one engine reading one composite under one condition."""
    engine_name: str
    condition_name: str
    plate_text: str
    clean_read: str
    decal_read: str
    clean_confidence: float
    decal_confidence: float

    @property
    def misread(self) -> bool:
        return self.clean_read != self.decal_read

    @property
    def confidence_delta(self) -> float:
        return self.decal_confidence - self.clean_confidence

    @property
    def corruption_type(self) -> str:
        """Classify the type of corruption."""
        if not self.misread:
            return "none"
        if len(self.decal_read) != len(self.clean_read):
            return "length_change"  # segmentation attack succeeded
        # Count character differences
        diffs = sum(1 for a, b in zip(self.clean_read, self.decal_read) if a != b)
        if diffs <= 2:
            return "char_substitution"  # confusion pair attack
        return "major_corruption"


@dataclass
class DecalScore:
    """Aggregated effectiveness score for a single decal."""
    decal_name: str
    strategy: str
    results: list[SingleResult] = field(default_factory=list)

    @property
    def total_reads(self) -> int:
        return len(self.results)

    @property
    def misread_count(self) -> int:
        return sum(1 for r in self.results if r.misread)

    @property
    def misread_rate(self) -> float:
        return self.misread_count / self.total_reads if self.total_reads > 0 else 0.0

    @property
    def avg_confidence_on_misreads(self) -> float:
        """Average confidence on misreads — higher = more dangerous corruption."""
        misreads = [r for r in self.results if r.misread]
        if not misreads:
            return 0.0
        return sum(r.decal_confidence for r in misreads) / len(misreads)

    @property
    def transferability(self) -> float:
        """Fraction of engines that were fooled (per-condition, then averaged)."""
        if not self.results:
            return 0.0
        by_condition: dict[str, dict[str, bool]] = {}
        for r in self.results:
            by_condition.setdefault(r.condition_name, {})[r.engine_name] = r.misread
        rates = []
        for cond, engines in by_condition.items():
            fooled = sum(1 for v in engines.values() if v)
            rates.append(fooled / len(engines))
        return sum(rates) / len(rates)

    @property
    def composite_score(self) -> float:
        """
        Single composite effectiveness score (0-100).

        Weights:
        - 40% misread rate (does it cause errors?)
        - 30% confidence on misreads (are errors confident / trusted?)
        - 30% transferability (does it work across engines?)
        """
        return (
            0.40 * self.misread_rate * 100
            + 0.30 * self.avg_confidence_on_misreads * 100
            + 0.30 * self.transferability * 100
        )

    @property
    def corruption_breakdown(self) -> dict[str, int]:
        """Count of each corruption type."""
        breakdown: dict[str, int] = {}
        for r in self.results:
            t = r.corruption_type
            breakdown[t] = breakdown.get(t, 0) + 1
        return breakdown

    def summary(self) -> dict:
        return {
            "decal": self.decal_name,
            "strategy": self.strategy,
            "composite_score": round(self.composite_score, 1),
            "misread_rate": round(self.misread_rate, 3),
            "avg_misread_confidence": round(self.avg_confidence_on_misreads, 3),
            "transferability": round(self.transferability, 3),
            "corruption_breakdown": self.corruption_breakdown,
            "total_reads": self.total_reads,
        }


def evaluate_decal(
    decal_image_path: str,
    plate_texts: Sequence[str] = ("ABC1234", "HBR4051", "WKM7793"),
    conditions: Sequence[ConditionSet] | None = None,
    engine_names: Sequence[str] | None = None,
    decal_name: str = "unknown",
    strategy: str = "unknown",
) -> DecalScore:
    """
    Evaluate a single decal across plates, conditions, and OCR engines.

    Creates composites under each condition, runs each engine, and returns
    an aggregated DecalScore.
    """
    from plate_compositor import create_composite, generate_test_plate, CompositeConfig
    from ocr_engines import get_engine, get_all_engines

    if conditions is None:
        conditions = STANDARD_CONDITIONS
    if engine_names is None:
        engines = get_all_engines()
    else:
        engines = []
        for name in engine_names:
            try:
                engines.append(get_engine(name))
            except Exception:
                pass

    if not engines:
        raise RuntimeError("No OCR engines available for evaluation")

    score = DecalScore(decal_name=decal_name, strategy=strategy)

    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)

        for plate_text in plate_texts:
            # Generate clean plate
            plate_path = tmp / f"plate_{plate_text}.png"
            generate_test_plate(plate_text=plate_text, output_path=str(plate_path))

            # Get clean reads from each engine
            clean_reads: dict[str, tuple[str, float]] = {}
            for engine in engines:
                try:
                    result = engine.read_plate(str(plate_path))
                    clean_reads[engine.name] = (result.plate_text, result.confidence)
                except Exception:
                    clean_reads[engine.name] = ("", 0.0)

            # Test under each condition
            for cond in conditions:
                composite_path = tmp / f"comp_{plate_text}_{cond.name}.png"

                config = CompositeConfig(
                    decal_position="below",
                    distance_ft=cond.distance_ft,
                    angle_deg=cond.angle_deg,
                    motion_blur_px=cond.motion_blur_px,
                    simulate_ir=cond.simulate_ir,
                    ir_wavelength_nm=cond.ir_wavelength_nm,
                )

                create_composite(
                    plate_image_path=str(plate_path),
                    decal_image_path=decal_image_path,
                    config=config,
                    output_path=str(composite_path),
                )

                # Read with each engine
                for engine in engines:
                    try:
                        result = engine.read_plate(str(composite_path))
                        clean_text, clean_conf = clean_reads.get(
                            engine.name, ("", 0.0)
                        )
                        score.results.append(SingleResult(
                            engine_name=engine.name,
                            condition_name=cond.name,
                            plate_text=plate_text,
                            clean_read=clean_text,
                            decal_read=result.plate_text,
                            clean_confidence=clean_conf,
                            decal_confidence=result.confidence,
                        ))
                    except Exception:
                        pass

    return score


def evaluate_suite(
    decal_dir: str,
    plate_texts: Sequence[str] = ("ABC1234", "HBR4051", "WKM7793"),
    conditions: Sequence[ConditionSet] | None = None,
    engine_names: Sequence[str] | None = None,
) -> list[DecalScore]:
    """
    Evaluate all decals in a directory and return ranked results.

    Scans for .png files, evaluates each, and returns scores sorted by
    composite effectiveness score (best first).
    """
    decal_dir_path = Path(decal_dir)
    if not decal_dir_path.exists():
        raise FileNotFoundError(f"Decal directory not found: {decal_dir}")

    decals = list(decal_dir_path.glob("*.png"))
    if not decals:
        raise FileNotFoundError(f"No .png decals found in {decal_dir}")

    scores = []
    for decal_path in decals:
        # Infer strategy from filename convention (strategy_vN.png)
        name = decal_path.stem
        strategy = name.rsplit("_v", 1)[0] if "_v" in name else "unknown"

        score = evaluate_decal(
            decal_image_path=str(decal_path),
            plate_texts=plate_texts,
            conditions=conditions,
            engine_names=engine_names,
            decal_name=name,
            strategy=strategy,
        )
        scores.append(score)

    # Sort by composite score (best first)
    scores.sort(key=lambda s: s.composite_score, reverse=True)
    return scores


def print_leaderboard(scores: list[DecalScore]) -> str:
    """Format evaluation results as a ranked leaderboard."""
    lines = [
        "=" * 80,
        "DECAL EFFECTIVENESS LEADERBOARD",
        "=" * 80,
        f"{'Rank':<5} {'Decal':<25} {'Strategy':<18} {'Score':<8} "
        f"{'Misread%':<10} {'Conf':<8} {'Transfer':<10}",
        "-" * 80,
    ]

    for i, score in enumerate(scores, 1):
        lines.append(
            f"{i:<5} {score.decal_name:<25} {score.strategy:<18} "
            f"{score.composite_score:<8.1f} "
            f"{score.misread_rate*100:<10.1f} "
            f"{score.avg_confidence_on_misreads:<8.3f} "
            f"{score.transferability*100:<10.1f}"
        )

    lines.append("=" * 80)

    # Corruption type breakdown for top 3
    for i, score in enumerate(scores[:3], 1):
        bd = score.corruption_breakdown
        lines.append(f"\n#{i} {score.decal_name} corruption types: {bd}")

    report = "\n".join(lines)
    return report


def export_results(scores: list[DecalScore], output_path: str) -> None:
    """Export evaluation results to JSON for further analysis."""
    data = [s.summary() for s in scores]
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
