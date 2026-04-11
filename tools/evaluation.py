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
    angle_deg: float = 0.0         # legacy alias for yaw_deg
    yaw_deg: float = 0.0           # horizontal camera offset
    pitch_deg: float = 0.0         # vertical camera offset (pole mount)
    motion_blur_px: int = 0
    simulate_ir: bool = False
    ir_wavelength_nm: int = 850


# Standard condition sets representing typical Flock capture scenarios
STANDARD_CONDITIONS = [
    ConditionSet("ideal", distance_ft=20.0),
    ConditionSet("mid_range", distance_ft=35.0),
    ConditionSet("far", distance_ft=50.0),
    ConditionSet("angled", distance_ft=25.0, yaw_deg=15.0),
    ConditionSet("angled_pitch", distance_ft=25.0, yaw_deg=8.0, pitch_deg=10.0),
    ConditionSet("motion", distance_ft=25.0, motion_blur_px=8),
    ConditionSet("ir_850nm", distance_ft=25.0, simulate_ir=True, ir_wavelength_nm=850),
    ConditionSet("ir_940nm", distance_ft=25.0, simulate_ir=True, ir_wavelength_nm=940),
    ConditionSet("worst_case", distance_ft=45.0, yaw_deg=10.0, pitch_deg=5.0, motion_blur_px=5),
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

    @property
    def misread_is_plausible(self) -> bool:
        """Check if the misread would survive Flock's format validation.

        A misread that doesn't match any US state plate format would likely
        be discarded by Flock's pipeline.  Only plausible misreads persist
        as ground truth in the database — these are the dangerous ones.
        """
        if not self.misread:
            return False
        try:
            from plate_formats import is_plausible_plate
            return is_plausible_plate(self.decal_read)
        except ImportError:
            return True  # can't check without plate_formats module


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
    def plausible_misread_rate(self) -> float:
        """Fraction of misreads that match a valid US plate format.

        This is the most operationally significant metric: only plausible
        misreads survive into Flock's database as ground truth.
        """
        misreads = [r for r in self.results if r.misread]
        if not misreads:
            return 0.0
        plausible = sum(1 for r in misreads if r.misread_is_plausible)
        return plausible / len(misreads)

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
            "plausible_misread_rate": round(self.plausible_misread_rate, 3),
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
                    yaw_deg=cond.yaw_deg,
                    pitch_deg=cond.pitch_deg,
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


# ═══════════════════════════════════════════════════════════════════════════
# Cross-Engine Transferability Matrix
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class TransferabilityCell:
    """One cell in the transferability matrix: source engine -> target engine."""
    source_engine: str
    target_engine: str
    co_misread_count: int = 0
    source_misread_count: int = 0

    @property
    def transfer_rate(self) -> float:
        """When source misreads, how often does target also misread?"""
        if self.source_misread_count == 0:
            return 0.0
        return self.co_misread_count / self.source_misread_count


@dataclass
class TransferabilityMatrix:
    """
    NxN matrix showing pairwise engine-to-engine attack transfer rates.

    Cell (i, j) answers: "When engine i misreads due to a decal, how often
    does engine j also misread?" High off-diagonal values indicate shared
    failure modes — attacks that transfer across architectures.

    This is the key metric for estimating effectiveness against Flock's
    unknown proprietary OCR: if a decal fools all three test engines, it
    likely exploits a fundamental OCR weakness rather than an engine-specific
    quirk (Vulnerability Catalog §2.3).
    """
    engines: list[str]
    cells: dict[tuple[str, str], TransferabilityCell] = field(default_factory=dict)
    strategy_matrices: dict[str, dict[tuple[str, str], TransferabilityCell]] = field(
        default_factory=dict
    )

    def rate(self, source: str, target: str) -> float:
        """Get transfer rate from source engine to target engine."""
        cell = self.cells.get((source, target))
        return cell.transfer_rate if cell else 0.0

    def strategy_rate(self, strategy: str, source: str, target: str) -> float:
        """Get transfer rate for a specific attack strategy."""
        strat_cells = self.strategy_matrices.get(strategy, {})
        cell = strat_cells.get((source, target))
        return cell.transfer_rate if cell else 0.0

    @property
    def mean_off_diagonal(self) -> float:
        """Average off-diagonal transfer rate — overall cross-engine attack success."""
        rates = [
            cell.transfer_rate
            for (src, tgt), cell in self.cells.items()
            if src != tgt and cell.source_misread_count > 0
        ]
        return sum(rates) / len(rates) if rates else 0.0

    @property
    def universal_misread_rate(self) -> float:
        """Fraction of reads where ALL engines were simultaneously fooled."""
        # Computed from the minimum per-engine transfer rate per row
        if len(self.engines) < 2:
            return 0.0
        # For each source engine, the minimum transfer rate to any other engine
        min_rates = []
        for src in self.engines:
            rates = [self.rate(src, tgt) for tgt in self.engines if tgt != src]
            if rates:
                min_rates.append(min(rates))
        return sum(min_rates) / len(min_rates) if min_rates else 0.0

    def summary(self) -> dict:
        """Serializable summary of the matrix."""
        matrix = {}
        for src in self.engines:
            matrix[src] = {}
            for tgt in self.engines:
                matrix[src][tgt] = round(self.rate(src, tgt), 3)

        strategy_breakdown = {}
        for strategy, cells in self.strategy_matrices.items():
            strategy_breakdown[strategy] = {}
            for src in self.engines:
                strategy_breakdown[strategy][src] = {}
                for tgt in self.engines:
                    cell = cells.get((src, tgt))
                    strategy_breakdown[strategy][src][tgt] = (
                        round(cell.transfer_rate, 3) if cell else 0.0
                    )

        return {
            "engines": self.engines,
            "matrix": matrix,
            "mean_off_diagonal_transfer": round(self.mean_off_diagonal, 3),
            "universal_misread_rate": round(self.universal_misread_rate, 3),
            "per_strategy": strategy_breakdown,
        }


def compute_transferability_matrix(
    scores: list[DecalScore],
) -> TransferabilityMatrix:
    """
    Build a cross-engine transferability matrix from evaluation results.

    Groups results by (plate_text, condition_name, decal_name) to find cases
    where the same input was tested across multiple engines.  For each such
    group, records which engines misread and which didn't, producing pairwise
    transfer rates.
    """
    # Discover all engines across all scores
    all_engines: set[str] = set()
    for score in scores:
        for r in score.results:
            all_engines.add(r.engine_name)
    engines = sorted(all_engines)

    matrix = TransferabilityMatrix(engines=engines)

    # Initialize cells
    for src in engines:
        for tgt in engines:
            matrix.cells[(src, tgt)] = TransferabilityCell(src, tgt)

    # Group results by (decal, plate, condition) — these are "same input" sets
    groups: dict[tuple[str, str, str], dict[str, bool]] = {}
    strategy_map: dict[tuple[str, str, str], str] = {}

    for score in scores:
        for r in score.results:
            key = (score.decal_name, r.plate_text, r.condition_name)
            groups.setdefault(key, {})[r.engine_name] = r.misread
            strategy_map[key] = score.strategy

    # Fill the matrix
    for key, engine_results in groups.items():
        strategy = strategy_map[key]

        # Ensure per-strategy cells exist
        if strategy not in matrix.strategy_matrices:
            matrix.strategy_matrices[strategy] = {}
            for src in engines:
                for tgt in engines:
                    matrix.strategy_matrices[strategy][(src, tgt)] = (
                        TransferabilityCell(src, tgt)
                    )

        for src in engines:
            if src not in engine_results:
                continue
            src_misread = engine_results[src]
            if not src_misread:
                continue

            for tgt in engines:
                if tgt not in engine_results:
                    continue

                # Source misread — count it
                matrix.cells[(src, tgt)].source_misread_count += 1
                matrix.strategy_matrices[strategy][(src, tgt)].source_misread_count += 1

                if engine_results[tgt]:
                    matrix.cells[(src, tgt)].co_misread_count += 1
                    matrix.strategy_matrices[strategy][(src, tgt)].co_misread_count += 1

    return matrix


def print_transferability_matrix(matrix: TransferabilityMatrix) -> str:
    """
    Format the transferability matrix as an ASCII table suitable for display.

    Produces output like:

        CROSS-ENGINE TRANSFERABILITY MATRIX
        ══════════════════════════════════════
        When source (row) misreads, how often does target (col) also misread?

                        tesseract   easyocr   paddleocr
        tesseract         1.000      0.720      0.540
        easyocr           0.680      1.000      0.610
        paddleocr         0.510      0.590      1.000

        Mean off-diagonal transfer: 62.0%
        Universal misread rate:     51.0%
    """
    engines = matrix.engines
    col_width = max(12, max((len(e) for e in engines), default=8) + 2)

    lines = [
        "",
        "=" * (col_width * (len(engines) + 1) + 4),
        "CROSS-ENGINE TRANSFERABILITY MATRIX",
        "=" * (col_width * (len(engines) + 1) + 4),
        "When source (row) misreads, how often does target (col) also misread?",
        "",
    ]

    # Header row
    header = " " * col_width + "".join(e.rjust(col_width) for e in engines)
    lines.append(header)
    lines.append("-" * len(header))

    # Data rows
    for src in engines:
        row = src.ljust(col_width)
        for tgt in engines:
            rate = matrix.rate(src, tgt)
            cell_str = f"{rate:.3f}"
            row += cell_str.rjust(col_width)
        lines.append(row)

    lines.append("")
    lines.append(f"Mean off-diagonal transfer: {matrix.mean_off_diagonal * 100:.1f}%")
    lines.append(f"Universal misread rate:     {matrix.universal_misread_rate * 100:.1f}%")

    # Per-strategy breakdown (if multiple strategies present)
    strategies = sorted(matrix.strategy_matrices.keys())
    if len(strategies) > 1:
        lines.append("")
        lines.append("-" * len(header))
        lines.append("PER-STRATEGY TRANSFER RATES (off-diagonal mean)")
        lines.append("-" * len(header))

        for strategy in strategies:
            strat_cells = matrix.strategy_matrices[strategy]
            rates = [
                cell.transfer_rate
                for (src, tgt), cell in strat_cells.items()
                if src != tgt and cell.source_misread_count > 0
            ]
            mean_rate = sum(rates) / len(rates) if rates else 0.0
            lines.append(f"  {strategy:<22} {mean_rate * 100:5.1f}%")

        # Full per-strategy matrices
        for strategy in strategies:
            lines.append("")
            lines.append(f"  [{strategy}]")
            header_row = "  " + " " * col_width + "".join(
                e.rjust(col_width) for e in engines
            )
            lines.append(header_row)
            for src in engines:
                row = "  " + src.ljust(col_width)
                for tgt in engines:
                    rate = matrix.strategy_rate(strategy, src, tgt)
                    row += f"{rate:.3f}".rjust(col_width)
                lines.append(row)

    lines.append("=" * (col_width * (len(engines) + 1) + 4))
    return "\n".join(lines)
