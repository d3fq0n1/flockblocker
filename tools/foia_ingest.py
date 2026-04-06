"""
FOIA image ingestion pipeline.

Normalizes, catalogs, and benchmarks real Flock camera captures obtained
through public records requests.  Bridges the sim-to-real gap by running
the existing evaluation pipeline against actual camera imagery.

Pipeline stages:
    1. **Ingest** — scan a directory of raw FOIA images
    2. **Normalize** — crop to plate region, standardize resolution
    3. **Label** — assign ground-truth plate text (manual or OCR-assisted)
    4. **Catalog** — produce a JSON manifest for reproducible benchmarking
    5. **Benchmark** — run evaluation pipeline against real captures

Until real FOIA images arrive, the pipeline ships with synthetic
placeholder images that exercise the full workflow.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import numpy as np

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError:
    Image = None


# ═══════════════════════════════════════════════════════════════════════════
# Data model
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class FOIAImage:
    """Metadata for a single FOIA-sourced camera capture."""
    image_id: str                      # UUID
    source_file: str                   # original filename
    normalized_path: str | None = None # path after normalization
    ground_truth: str = ""             # actual plate text (manually verified)
    ocr_assisted_text: str = ""        # OCR suggestion (for labeling assistance)
    confidence: float = 0.0            # OCR confidence of assisted read
    state: str = ""                    # plate state (2-letter code)
    camera_id: str = ""                # Flock camera identifier (from FOIA metadata)
    capture_timestamp: str = ""        # ISO-8601 timestamp (from FOIA metadata)
    location: str = ""                 # camera location description
    source_hash: str = ""              # SHA-256 of original file (integrity check)
    notes: str = ""                    # researcher notes
    is_placeholder: bool = False       # True for synthetic test images

    def to_dict(self) -> dict:
        return {
            "image_id": self.image_id,
            "source_file": self.source_file,
            "normalized_path": self.normalized_path,
            "ground_truth": self.ground_truth,
            "ocr_assisted_text": self.ocr_assisted_text,
            "confidence": self.confidence,
            "state": self.state,
            "camera_id": self.camera_id,
            "capture_timestamp": self.capture_timestamp,
            "location": self.location,
            "source_hash": self.source_hash,
            "notes": self.notes,
            "is_placeholder": self.is_placeholder,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "FOIAImage":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class FOIACatalog:
    """Manifest of all ingested FOIA images."""
    catalog_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    images: list[FOIAImage] = field(default_factory=list)
    source_description: str = ""       # FOIA request reference
    agency: str = ""                   # responding agency name

    @property
    def total_images(self) -> int:
        return len(self.images)

    @property
    def labeled_count(self) -> int:
        return sum(1 for img in self.images if img.ground_truth)

    @property
    def placeholder_count(self) -> int:
        return sum(1 for img in self.images if img.is_placeholder)

    def to_dict(self) -> dict:
        return {
            "catalog_id": self.catalog_id,
            "created_at": self.created_at,
            "source_description": self.source_description,
            "agency": self.agency,
            "total_images": self.total_images,
            "labeled_count": self.labeled_count,
            "placeholder_count": self.placeholder_count,
            "images": [img.to_dict() for img in self.images],
        }

    def save(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> "FOIACatalog":
        with open(path) as f:
            data = json.load(f)
        catalog = cls(
            catalog_id=data.get("catalog_id", str(uuid.uuid4())),
            created_at=data.get("created_at", ""),
            source_description=data.get("source_description", ""),
            agency=data.get("agency", ""),
        )
        for img_data in data.get("images", []):
            catalog.images.append(FOIAImage.from_dict(img_data))
        return catalog


# ═══════════════════════════════════════════════════════════════════════════
# Stage 1: Ingest — scan raw images
# ═══════════════════════════════════════════════════════════════════════════

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}


def ingest_directory(
    raw_dir: str,
    source_description: str = "",
    agency: str = "",
) -> FOIACatalog:
    """Scan a directory of raw FOIA images and create a catalog.

    Args:
        raw_dir: Path to directory containing raw camera captures.
        source_description: Reference to the FOIA request.
        agency: Name of the responding agency.

    Returns:
        FOIACatalog with entries for each discovered image.
    """
    raw_path = Path(raw_dir)
    if not raw_path.exists():
        raise FileNotFoundError(f"Directory not found: {raw_dir}")

    catalog = FOIACatalog(
        source_description=source_description,
        agency=agency,
    )

    for ext in sorted(SUPPORTED_EXTENSIONS):
        for img_path in sorted(raw_path.glob(f"*{ext}")):
            file_hash = _compute_file_hash(img_path)
            entry = FOIAImage(
                image_id=str(uuid.uuid4()),
                source_file=img_path.name,
                source_hash=file_hash,
            )
            catalog.images.append(entry)

    return catalog


def _compute_file_hash(path: Path) -> str:
    """SHA-256 hash of file contents (truncated to 16 hex chars)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


# ═══════════════════════════════════════════════════════════════════════════
# Stage 2: Normalize — crop and standardize
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class NormalizeConfig:
    """Configuration for image normalization."""
    target_width: int = 640        # output width
    target_height: int = 480       # output height
    plate_region: tuple | None = None  # (x1, y1, x2, y2) crop box, None = auto
    grayscale: bool = False        # convert to grayscale (matches IR capture)
    enhance_contrast: bool = True  # apply histogram equalization


def normalize_image(
    source_path: str,
    output_path: str,
    config: NormalizeConfig | None = None,
) -> dict:
    """Normalize a raw FOIA image for evaluation.

    1. Crop to plate region (if specified or auto-detected)
    2. Resize to standard dimensions
    3. Optionally convert to grayscale
    4. Optionally enhance contrast

    Returns:
        Dict with normalization metadata (crop box, scale factor, etc.)
    """
    if Image is None:
        raise ImportError("Pillow is required: pip install Pillow")

    config = config or NormalizeConfig()
    img = Image.open(source_path).convert("RGB")
    original_size = img.size
    metadata = {"original_size": original_size}

    # Crop to plate region
    if config.plate_region:
        img = img.crop(config.plate_region)
        metadata["crop_box"] = config.plate_region
    else:
        # Auto-crop: use center 60% of image (heuristic for plate-centered captures)
        w, h = img.size
        margin_x = int(w * 0.2)
        margin_y = int(h * 0.2)
        crop_box = (margin_x, margin_y, w - margin_x, h - margin_y)
        img = img.crop(crop_box)
        metadata["crop_box"] = crop_box
        metadata["crop_method"] = "auto_center_60pct"

    # Resize to target dimensions
    img = img.resize(
        (config.target_width, config.target_height),
        Image.LANCZOS,
    )
    metadata["target_size"] = (config.target_width, config.target_height)

    # Grayscale conversion
    if config.grayscale:
        img = img.convert("L").convert("RGB")  # back to RGB for compatibility
        metadata["grayscale"] = True

    # Contrast enhancement via histogram equalization
    if config.enhance_contrast:
        img = _enhance_contrast(img)
        metadata["contrast_enhanced"] = True

    img.save(output_path)
    metadata["output_path"] = output_path
    return metadata


def _enhance_contrast(image: "Image.Image") -> "Image.Image":
    """Apply simple histogram stretching for contrast enhancement."""
    arr = np.array(image, dtype=np.float32)
    for c in range(3):
        channel = arr[:, :, c]
        lo, hi = np.percentile(channel, [2, 98])
        if hi - lo > 0:
            arr[:, :, c] = np.clip((channel - lo) / (hi - lo) * 255, 0, 255)
    return Image.fromarray(arr.astype(np.uint8))


def normalize_catalog(
    catalog: FOIACatalog,
    raw_dir: str,
    output_dir: str,
    config: NormalizeConfig | None = None,
) -> FOIACatalog:
    """Normalize all images in a catalog.

    Args:
        catalog: The catalog to process.
        raw_dir: Directory containing original images.
        output_dir: Directory for normalized output.
        config: Normalization settings.

    Returns:
        Updated catalog with normalized_path set for each image.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    for entry in catalog.images:
        source = Path(raw_dir) / entry.source_file
        if not source.exists():
            continue
        dest = out / f"{entry.image_id}.png"
        normalize_image(str(source), str(dest), config)
        entry.normalized_path = str(dest)

    return catalog


# ═══════════════════════════════════════════════════════════════════════════
# Stage 3: OCR-assisted labeling
# ═══════════════════════════════════════════════════════════════════════════

def ocr_assist_labeling(
    catalog: FOIACatalog,
    engine_names: Sequence[str] | None = None,
) -> FOIACatalog:
    """Run OCR on normalized images to assist with ground-truth labeling.

    For each image without a ground_truth label, runs available OCR engines
    and stores the highest-confidence read as ``ocr_assisted_text``.  A human
    researcher then verifies/corrects these suggestions.

    Args:
        catalog: Catalog with normalized_path set.
        engine_names: Which OCR engines to use. None = all available.

    Returns:
        Updated catalog with ocr_assisted_text populated.
    """
    try:
        from ocr_engines import get_engine, get_all_engines
    except ImportError:
        return catalog

    if engine_names:
        engines = []
        for name in engine_names:
            try:
                engines.append(get_engine(name))
            except Exception:
                pass
    else:
        engines = get_all_engines()

    if not engines:
        return catalog

    for entry in catalog.images:
        if entry.ground_truth:
            continue  # already labeled
        if not entry.normalized_path or not Path(entry.normalized_path).exists():
            continue

        best_text = ""
        best_conf = 0.0

        for engine in engines:
            try:
                result = engine.read_plate(entry.normalized_path)
                if result.confidence > best_conf:
                    best_conf = result.confidence
                    best_text = result.plate_text
            except Exception:
                continue

        entry.ocr_assisted_text = best_text
        entry.confidence = best_conf

    return catalog


# ═══════════════════════════════════════════════════════════════════════════
# Stage 4: Benchmark against evaluation pipeline
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class BenchmarkResult:
    """Results from benchmarking against real FOIA captures."""
    total_images: int
    labeled_images: int
    engine_results: dict[str, EngineAccuracy] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "total_images": self.total_images,
            "labeled_images": self.labeled_images,
            "engines": {
                name: acc.to_dict()
                for name, acc in self.engine_results.items()
            },
        }


@dataclass
class EngineAccuracy:
    """Accuracy metrics for one engine against ground-truth labels."""
    engine_name: str
    total_reads: int = 0
    exact_matches: int = 0
    partial_matches: int = 0     # ≥80% character match
    total_confidence: float = 0.0
    misreads: list[dict] = field(default_factory=list)  # {expected, got, confidence}

    @property
    def exact_accuracy(self) -> float:
        return self.exact_matches / self.total_reads if self.total_reads else 0.0

    @property
    def partial_accuracy(self) -> float:
        return (self.exact_matches + self.partial_matches) / self.total_reads if self.total_reads else 0.0

    @property
    def avg_confidence(self) -> float:
        return self.total_confidence / self.total_reads if self.total_reads else 0.0

    def to_dict(self) -> dict:
        return {
            "engine": self.engine_name,
            "total_reads": self.total_reads,
            "exact_accuracy": round(self.exact_accuracy, 3),
            "partial_accuracy": round(self.partial_accuracy, 3),
            "avg_confidence": round(self.avg_confidence, 3),
            "misread_count": len(self.misreads),
            "misreads": self.misreads[:10],  # first 10 for brevity
        }


def _char_match_ratio(expected: str, got: str) -> float:
    """Fraction of characters matching (position-aligned)."""
    if not expected:
        return 0.0
    matches = sum(1 for a, b in zip(expected, got) if a == b)
    return matches / max(len(expected), len(got))


def benchmark_catalog(
    catalog: FOIACatalog,
    engine_names: Sequence[str] | None = None,
) -> BenchmarkResult:
    """Benchmark OCR engines against ground-truth-labeled FOIA captures.

    Only processes images that have both a normalized_path and ground_truth.

    Args:
        catalog: Catalog with labeled images.
        engine_names: Which engines to test. None = all available.

    Returns:
        BenchmarkResult with per-engine accuracy metrics.
    """
    try:
        from ocr_engines import get_engine, get_all_engines
    except ImportError:
        return BenchmarkResult(total_images=catalog.total_images, labeled_images=0)

    if engine_names:
        engines = []
        for name in engine_names:
            try:
                engines.append(get_engine(name))
            except Exception:
                pass
    else:
        engines = get_all_engines()

    labeled = [
        img for img in catalog.images
        if img.ground_truth and img.normalized_path
        and Path(img.normalized_path).exists()
    ]

    result = BenchmarkResult(
        total_images=catalog.total_images,
        labeled_images=len(labeled),
    )

    for engine in engines:
        acc = EngineAccuracy(engine_name=engine.name)

        for entry in labeled:
            try:
                ocr_result = engine.read_plate(entry.normalized_path)
                acc.total_reads += 1
                acc.total_confidence += ocr_result.confidence

                expected = entry.ground_truth.upper().replace(" ", "").replace("-", "")
                got = ocr_result.plate_text

                if got == expected:
                    acc.exact_matches += 1
                elif _char_match_ratio(expected, got) >= 0.8:
                    acc.partial_matches += 1
                else:
                    acc.misreads.append({
                        "expected": expected,
                        "got": got,
                        "confidence": round(ocr_result.confidence, 3),
                        "image_id": entry.image_id,
                    })
            except Exception:
                continue

        result.engine_results[engine.name] = acc

    return result


# ═══════════════════════════════════════════════════════════════════════════
# Placeholder image generator
# ═══════════════════════════════════════════════════════════════════════════

def generate_placeholders(
    output_dir: str,
    count: int = 10,
    seed: int = 42,
) -> FOIACatalog:
    """Generate synthetic placeholder FOIA images for pipeline testing.

    Creates realistic-ish camera capture simulations with:
    - Synthetic plates at varying distances/angles
    - IR-like grayscale rendering
    - Motion blur and noise
    - Environmental context (dark background simulating nighttime)

    These exercise the full ingestion pipeline until real FOIA images arrive.

    Args:
        output_dir: Directory to write placeholder images.
        count: Number of images to generate.
        seed: Random seed for reproducibility.

    Returns:
        FOIACatalog with all generated images (ground_truth pre-filled).
    """
    if Image is None:
        raise ImportError("Pillow is required: pip install Pillow")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    rng = np.random.RandomState(seed)
    py_rng = random.Random(seed)

    # Import plate generation
    try:
        from plate_formats import generate_plate, STATE_FORMATS
        states = list(STATE_FORMATS.keys())
    except ImportError:
        states = ["WI", "GA", "CA", "TX", "FL", "NY"]

    catalog = FOIACatalog(
        source_description="Synthetic placeholders for pipeline testing",
        agency="FlockBlocker Research (synthetic)",
    )

    # Plate font
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60
        )
        font_small = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20
        )
    except (OSError, IOError):
        font = ImageFont.load_default()
        font_small = font

    for i in range(count):
        state = py_rng.choice(states)
        try:
            plate_text = generate_plate(state, seed=seed + i)
        except Exception:
            plate_text = f"{''.join(py_rng.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=3))}{''.join(py_rng.choices('0123456789', k=4))}"

        # Create a simulated camera capture scene
        scene_w, scene_h = 800, 600
        # Dark background (nighttime capture with IR illumination)
        bg_val = rng.randint(20, 50)
        scene = Image.new("RGB", (scene_w, scene_h), (bg_val, bg_val, bg_val))
        draw = ImageDraw.Draw(scene)

        # Draw plate in scene (centered, with some random offset)
        plate_w, plate_h = 300, 150
        plate_x = scene_w // 2 - plate_w // 2 + rng.randint(-40, 40)
        plate_y = scene_h // 2 - plate_h // 2 + rng.randint(-30, 30)

        # White plate rectangle
        draw.rectangle(
            [plate_x, plate_y, plate_x + plate_w, plate_y + plate_h],
            fill=(240, 240, 240),
            outline=(0, 0, 0),
            width=2,
        )

        # State text
        bbox = draw.textbbox((0, 0), state, font=font_small)
        sw = bbox[2] - bbox[0]
        draw.text(
            (plate_x + (plate_w - sw) // 2, plate_y + 8),
            state,
            fill=(0, 0, 80),
            font=font_small,
        )

        # Plate text
        bbox = draw.textbbox((0, 0), plate_text, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(
            (plate_x + (plate_w - tw) // 2, plate_y + 40),
            plate_text,
            fill=(10, 10, 10),
            font=font,
        )

        # Add vehicle body context (dark rectangle around plate)
        bumper_margin = 30
        draw.rectangle(
            [plate_x - bumper_margin, plate_y - bumper_margin,
             plate_x + plate_w + bumper_margin, plate_y + plate_h + bumper_margin],
            outline=(60, 60, 70),
            width=3,
        )

        # Simulate capture conditions
        arr = np.array(scene, dtype=np.float32)

        # Distance-based blur (random 20-45 ft)
        distance = 20 + rng.random() * 25
        if distance > 25:
            sigma = (distance - 25) / 10.0
            scene = scene.filter(ImageFilter.GaussianBlur(radius=sigma))
            arr = np.array(scene, dtype=np.float32)

        # Add sensor noise
        noise = rng.normal(0, 8, arr.shape)
        arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
        scene = Image.fromarray(arr)

        # Random chance of IR simulation (60% of captures are IR)
        is_ir = rng.random() < 0.6
        if is_ir:
            from ir_simulation import simulate_ir
            wavelength = py_rng.choice([850, 940])
            scene = simulate_ir(scene, wavelength)

        # Save
        filename = f"foia_placeholder_{i:04d}.png"
        filepath = out / filename
        scene.save(str(filepath))

        entry = FOIAImage(
            image_id=str(uuid.uuid4()),
            source_file=filename,
            ground_truth=plate_text,
            state=state,
            capture_timestamp=datetime.now(timezone.utc).isoformat(),
            source_hash=_compute_file_hash(filepath),
            notes=f"Synthetic placeholder. Distance: {distance:.0f}ft. IR: {is_ir}",
            is_placeholder=True,
        )
        catalog.images.append(entry)

    # Save catalog
    catalog_path = out / "catalog.json"
    catalog.save(str(catalog_path))

    return catalog


# ═══════════════════════════════════════════════════════════════════════════
# CLI convenience
# ═══════════════════════════════════════════════════════════════════════════

import random  # needed for generate_placeholders


def print_benchmark_report(result: BenchmarkResult) -> str:
    """Format benchmark results as an ASCII report."""
    lines = [
        "=" * 70,
        "FOIA IMAGE BENCHMARK REPORT",
        "=" * 70,
        f"Total images: {result.total_images}",
        f"Labeled images: {result.labeled_images}",
        "",
        f"{'Engine':<15} {'Exact%':<10} {'Partial%':<10} "
        f"{'AvgConf':<10} {'Misreads':<10}",
        "-" * 70,
    ]

    for name, acc in result.engine_results.items():
        lines.append(
            f"{name:<15} {acc.exact_accuracy*100:<10.1f} "
            f"{acc.partial_accuracy*100:<10.1f} "
            f"{acc.avg_confidence:<10.3f} {len(acc.misreads):<10}"
        )

    lines.append("=" * 70)

    # Show worst misreads
    for name, acc in result.engine_results.items():
        if acc.misreads:
            lines.append(f"\n{name} misreads (first 5):")
            for mr in acc.misreads[:5]:
                lines.append(
                    f"  expected={mr['expected']} got={mr['got']} "
                    f"conf={mr['confidence']}"
                )

    return "\n".join(lines)
