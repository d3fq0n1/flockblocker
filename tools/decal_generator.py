"""
Adversarial decal generator for LPR/OCR corruption.

Generates decal images designed to corrupt Flock Safety camera reads through
four distinct attack strategies:

1. Character Confusion    (§1.1) — Ambiguous characters bleed into plate read
2. Segmentation Boundary  (§1.2) — Extend plate boundary into sticker region
3. IR Phantom Injection   (§3.3) — Colors collapse to plate-like chars under IR
4. EOT Adversarial Patch  (§2.4) — Gradient-optimized patterns robust to transforms

Each generator produces PIL Images suitable for compositing via plate_compositor.
"""

from __future__ import annotations

import itertools
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

import numpy as np

from ir_simulation import simulate_ir

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError:
    Image = None

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

# Character confusion pairs from Vulnerability Catalog §1.1
CONFUSION_PAIRS: dict[str, list[str]] = {
    "0": ["O", "D", "Q"],
    "O": ["0", "D", "Q"],
    "D": ["0", "O", "Q"],
    "Q": ["0", "O", "D"],
    "1": ["I", "L"],
    "I": ["1", "L"],
    "L": ["1", "I"],
    "8": ["B"],
    "B": ["8"],
    "5": ["S"],
    "S": ["5"],
    "2": ["Z"],
    "Z": ["2"],
    "6": ["G"],
    "G": ["6"],
    "C": ["G", "O"],
    "M": ["N", "H"],
    "N": ["M", "H"],
    "H": ["M", "N"],
    "V": ["U", "Y"],
    "U": ["V", "Y"],
    "K": ["X"],
    "X": ["K"],
}

# Characters that appear on US plates (alpha + digits)
PLATE_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

# Standard US plate dimensions at typical bumper-sticker scale
DEFAULT_DECAL_WIDTH = 480
DEFAULT_DECAL_HEIGHT = 120

# Colors that collapse under 850nm IR (§3.3)
# Pairs: (visible_color_rgb, ir_equivalent_rgb) — look different to humans, same to IR
#
# Sweep-optimized pairs (from ir_color_sweep.py) maximize phantom_ratio
# (IR_contrast / visible_delta_e).  "Practical" pairs trade some ratio for
# real-world plausibility (a bright cyan bumper sticker draws attention).
#
# Sweep results (step=20, max_dE=5, min_ir=10):
#   850nm top: (0,240,240)/(20,240,240) — dE=0.51, IR_Δ=10, ratio=19.6
#   940nm top: (0,240,240)/(40,240,240) — dE=1.54, IR_Δ=16, ratio=10.4
IR_COLLAPSE_PAIRS_850 = [
    # Sweep-optimized: cyan with minimal red delta (dE < 1)
    ((0, 240, 240), (20, 240, 240)),
    ((0, 240, 220), (20, 240, 220)),
    # Practical: dark red pairs (plausible bumper sticker)
    ((180, 20, 20), (200, 40, 30)),
    ((160, 30, 25), (180, 20, 20)),
]

IR_COLLAPSE_PAIRS_940 = [
    # Sweep-optimized: cyan with moderate red delta
    ((0, 240, 240), (40, 240, 240)),
    ((0, 220, 240), (40, 220, 240)),
    # Practical: green/gray pairs (garden-variety sticker)
    ((40, 140, 40), (55, 130, 45)),
    ((30, 100, 30), (50, 90, 40)),
]

# Legacy alias (union of practical pairs) for backward compatibility
IR_COLLAPSE_PAIRS = [
    ((180, 20, 20), (30, 30, 30)),
    ((40, 140, 40), (110, 110, 110)),
    ((20, 20, 140), (80, 20, 120)),
    ((200, 40, 30), (50, 50, 50)),
    ((30, 100, 30), (90, 90, 90)),
]


def _load_plate_font(size: int) -> "ImageFont.FreeTypeFont":
    """Load a font resembling US plate typefaces."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


# ═══════════════════════════════════════════════════════════════════════════
# 1. Character Confusion Decal Generator (§1.1)
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ConfusionDecalConfig:
    """Config for character-confusion decal generation."""
    width: int = DEFAULT_DECAL_WIDTH
    height: int = DEFAULT_DECAL_HEIGHT
    # Characters to render on the decal — chosen for maximal confusion
    char_sequence: str | None = None  # auto-generate if None
    num_chars: int = 7  # match typical plate length
    font_size: int = 72
    # Styling to mimic plate appearance
    bg_color: tuple = (255, 255, 255)
    text_color: tuple = (0, 0, 0)
    # Add plate-like border to encourage segmentation bleed
    plate_mimicry: bool = True
    border_width: int = 2
    border_color: tuple = (0, 0, 0)


def generate_confusion_decal(
    config: ConfusionDecalConfig | None = None,
    target_plate: str | None = None,
    output_path: str | None = None,
) -> "Image.Image":
    """
    Generate a decal containing characters chosen to maximally confuse OCR.

    Strategy: Place characters from known confusion pairs near the plate so
    that if segmentation bleeds, the OCR reads ambiguous characters that
    corrupt the plate string.

    If target_plate is provided, generates confusion characters specifically
    chosen to create plausible misreads of that plate text.
    """
    if Image is None:
        raise ImportError("Pillow is required: pip install Pillow")

    config = config or ConfusionDecalConfig()

    if config.char_sequence:
        chars = config.char_sequence
    elif target_plate:
        chars = _generate_targeted_confusion(target_plate, config.num_chars)
    else:
        chars = _generate_random_confusion(config.num_chars)

    img = Image.new("RGB", (config.width, config.height), config.bg_color)
    draw = ImageDraw.Draw(img)

    if config.plate_mimicry:
        draw.rectangle(
            [1, 1, config.width - 2, config.height - 2],
            outline=config.border_color,
            width=config.border_width,
        )

    font = _load_plate_font(config.font_size)
    bbox = draw.textbbox((0, 0), chars, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (config.width - text_w) // 2
    y = (config.height - text_h) // 2
    draw.text((x, y), chars, fill=config.text_color, font=font)

    if output_path:
        img.save(output_path)
    return img


def _generate_targeted_confusion(plate_text: str, length: int) -> str:
    """Generate a string that, if appended/prepended, creates a plausible misread."""
    result = []
    for ch in plate_text.upper()[:length]:
        if ch in CONFUSION_PAIRS:
            result.append(random.choice(CONFUSION_PAIRS[ch]))
        else:
            # Use a random confusable character
            result.append(random.choice(list(CONFUSION_PAIRS.keys())))
    return "".join(result)


def _generate_random_confusion(length: int) -> str:
    """Generate a string of maximally confusable characters."""
    # Pick from characters that have the most confusion partners
    high_confusion = sorted(
        CONFUSION_PAIRS.keys(),
        key=lambda c: len(CONFUSION_PAIRS[c]),
        reverse=True,
    )
    pool = high_confusion[: max(8, len(high_confusion) // 2)]
    return "".join(random.choice(pool) for _ in range(length))


# ═══════════════════════════════════════════════════════════════════════════
# 2. Segmentation Boundary Attack Generator (§1.2)
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SegmentationDecalConfig:
    """Config for segmentation boundary attack decals."""
    width: int = DEFAULT_DECAL_WIDTH
    height: int = DEFAULT_DECAL_HEIGHT
    font_size: int = 72
    # Segmentation attack parameters
    bg_color: tuple = (255, 255, 255)  # match plate background
    text_color: tuple = (0, 0, 0)      # match plate text
    # Gap between decal edge and characters — smaller = more likely to merge
    edge_padding: int = 4
    # Characters to place at the boundary edge
    boundary_chars: str | None = None
    # Whether to add a continuous border that "extends" the plate edge
    extend_plate_border: bool = True
    border_thickness: int = 3


def generate_segmentation_decal(
    config: SegmentationDecalConfig | None = None,
    target_plate: str | None = None,
    output_path: str | None = None,
) -> "Image.Image":
    """
    Generate a decal designed to fool plate segmentation algorithms.

    Strategy: Create a sticker that visually extends the plate boundary so
    the segmentation algorithm includes sticker content in the plate region.
    Characters on the sticker are then read as part of the plate.

    Key design choices:
    - Match plate background color (white) and text color (dark)
    - Minimize gap between sticker edge and plate edge
    - Place characters at the boundary edge closest to the plate
    - Add border lines that continue the plate border
    """
    if Image is None:
        raise ImportError("Pillow is required: pip install Pillow")

    config = config or SegmentationDecalConfig()

    # Choose boundary characters — these will be read as plate extensions
    if config.boundary_chars:
        chars = config.boundary_chars
    elif target_plate:
        # Add characters that make the plate look like a different valid plate
        chars = _generate_segmentation_extension(target_plate)
    else:
        # Use characters commonly misread: mix of digits and confusables
        chars = random.choice(["0O0", "1I1", "B8B", "5S5", "Z2Z", "6G6"])

    img = Image.new("RGB", (config.width, config.height), config.bg_color)
    draw = ImageDraw.Draw(img)

    if config.extend_plate_border:
        # Draw border that matches plate border styling
        # Leave the edge closest to the plate OPEN to create visual continuity
        t = config.border_thickness
        # Top, left, right borders (bottom left open for "below" placement)
        draw.line([(0, 0), (config.width - 1, 0)], fill=(0, 0, 0), width=t)
        draw.line([(0, 0), (0, config.height - 1)], fill=(0, 0, 0), width=t)
        draw.line(
            [(config.width - 1, 0), (config.width - 1, config.height - 1)],
            fill=(0, 0, 0),
            width=t,
        )

    font = _load_plate_font(config.font_size)

    # Place characters tight against the top edge (closest to plate when below)
    bbox = draw.textbbox((0, 0), chars, font=font)
    text_w = bbox[2] - bbox[0]
    x = (config.width - text_w) // 2
    y = config.edge_padding
    draw.text((x, y), chars, fill=config.text_color, font=font)

    if output_path:
        img.save(output_path)
    return img


def _generate_segmentation_extension(plate_text: str) -> str:
    """Generate characters that extend a plate into a different valid read."""
    # Strategy: add 1-3 chars that change what the full string looks like
    extensions = []
    # Trailing digits/letters that shift the read
    if plate_text[-1].isdigit():
        extensions.append(str(random.randint(0, 9)) + random.choice("ODIBL"))
    else:
        extensions.append(random.choice("01856") + random.choice("ODIBL"))
    return random.choice(extensions)


# ═══════════════════════════════════════════════════════════════════════════
# 3. IR Phantom Character Injection (§3.3)
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class IRPhantomConfig:
    """Config for IR phantom character decals.

    Default colors are sweep-optimized (see ir_color_sweep.py) for maximum
    phantom_ratio at 850nm.  Pass ``use_practical_colors=True`` to use
    darker, less conspicuous pairs suitable for real-world stickers.
    """
    width: int = DEFAULT_DECAL_WIDTH
    height: int = DEFAULT_DECAL_HEIGHT
    font_size: int = 72
    # The IR wavelength to target
    target_wavelength_nm: int = 850
    # Background color (visible light) — should look like a normal design
    visible_bg_color: tuple | None = None
    # Text color (visible light) — should be nearly invisible to humans
    visible_text_color: tuple | None = None
    # Use practical (plausible bumper sticker) colors instead of
    # sweep-optimized max-ratio colors
    use_practical_colors: bool = False
    phantom_chars: str | None = None


def generate_ir_phantom_decal(
    config: IRPhantomConfig | None = None,
    target_plate: str | None = None,
    output_path: str | None = None,
) -> "Image.Image":
    """
    Generate a decal that hides characters visible only under IR illumination.

    Strategy: Exploit chromatic collapse under IR (§3.3). Use color pairs that:
    - Look like a normal solid-color sticker to human eyes
    - Under 850nm/940nm IR, the background and foreground collapse differently,
      revealing hidden characters to the camera

    The IR camera sees characters that humans don't. These phantom characters
    bleed into the plate segmentation region and corrupt the read.
    """
    if Image is None:
        raise ImportError("Pillow is required: pip install Pillow")

    config = config or IRPhantomConfig()

    chars = config.phantom_chars
    if chars is None:
        if target_plate:
            chars = _generate_targeted_confusion(target_plate, 5)
        else:
            chars = _generate_random_confusion(5)

    # Select an IR collapse pair based on target wavelength
    if config.visible_bg_color is not None and config.visible_text_color is not None:
        # Caller specified explicit colors — use as-is
        bg_vis = config.visible_bg_color
        text_vis = config.visible_text_color
    else:
        # Pick from wavelength-specific optimized pairs
        if config.target_wavelength_nm <= 850:
            pairs = IR_COLLAPSE_PAIRS_850
        else:
            pairs = IR_COLLAPSE_PAIRS_940

        # Index 0-1 = sweep-optimized, 2+ = practical
        idx = 2 if config.use_practical_colors else 0
        bg_vis, text_vis = pairs[idx]

    img = Image.new("RGB", (config.width, config.height), bg_vis)
    draw = ImageDraw.Draw(img)

    font = _load_plate_font(config.font_size)
    bbox = draw.textbbox((0, 0), chars, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (config.width - text_w) // 2
    y = (config.height - text_h) // 2
    draw.text((x, y), chars, fill=text_vis, font=font)

    if output_path:
        img.save(output_path)
    return img


def simulate_ir_view(
    image: "Image.Image",
    wavelength_nm: int = 850,
) -> "Image.Image":
    """
    Show what an IR camera sees — reveals hidden phantom characters.

    Delegates to :func:`ir_simulation.simulate_ir` (the single source of truth
    for IR sensor-response weights).
    """
    return simulate_ir(image, wavelength_nm)


# ═══════════════════════════════════════════════════════════════════════════
# 4. EOT Adversarial Patch Generator (§2.4)
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class AdversarialPatchConfig:
    """Config for EOT-optimized adversarial patch generation."""
    width: int = DEFAULT_DECAL_WIDTH
    height: int = DEFAULT_DECAL_HEIGHT
    # Optimization parameters
    num_steps: int = 500
    learning_rate: float = 0.02
    # EOT: number of random transforms per optimization step
    eot_samples: int = 10
    # Transform ranges for EOT robustness
    angle_range: tuple = (-15.0, 15.0)      # degrees
    scale_range: tuple = (0.6, 1.4)
    brightness_range: tuple = (0.7, 1.3)
    # Target behavior
    target_text: str | None = None   # targeted misread (None = untargeted)
    # Printability constraint: keep colors in CMYK gamut
    enforce_printability: bool = True
    # Total variation weight for smoothness (reduces print artifacts)
    tv_weight: float = 0.001
    # Seed for reproducibility
    seed: int | None = None


def generate_adversarial_patch(
    config: AdversarialPatchConfig | None = None,
    output_path: str | None = None,
) -> "Image.Image":
    """
    Generate an EOT-optimized adversarial patch that corrupts OCR reads.

    This is the heavyweight generator — uses PyTorch to optimize a printable
    pattern that maximally disrupts OCR character recognition across a
    distribution of viewing conditions (angle, scale, brightness).

    The patch is optimized against Tesseract's character classification to
    maximize cross-architecture transferability (§2.3).

    Returns a PIL Image of the optimized patch.
    """
    if Image is None:
        raise ImportError("Pillow is required: pip install Pillow")

    config = config or AdversarialPatchConfig()

    try:
        import torch
        import torch.nn.functional as F
    except ImportError:
        # Fallback: generate a high-frequency noise pattern that disrupts OCR
        # without gradient optimization
        return _generate_heuristic_patch(config, output_path)

    if config.seed is not None:
        torch.manual_seed(config.seed)
        np.random.seed(config.seed)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Initialize patch as learnable parameter (random colors)
    patch = torch.rand(1, 3, config.height, config.width, device=device) * 0.5 + 0.25
    patch = torch.nn.Parameter(patch)

    optimizer = torch.optim.Adam([patch], lr=config.learning_rate)

    for step in range(config.num_steps):
        optimizer.zero_grad()

        # Aggregate loss over EOT samples
        total_loss = torch.tensor(0.0, device=device)

        for _ in range(config.eot_samples):
            # Apply random transform (EOT)
            transformed = _apply_random_transform(patch, config, device)

            # Compute OCR disruption loss
            loss = _compute_disruption_loss(transformed, device)

            # Total variation penalty for printability
            if config.tv_weight > 0:
                loss = loss + config.tv_weight * _total_variation(transformed)

            total_loss = total_loss + loss

        total_loss = total_loss / config.eot_samples
        total_loss.backward()
        optimizer.step()

        # Clamp to valid pixel range
        with torch.no_grad():
            patch.data.clamp_(0.0, 1.0)
            if config.enforce_printability:
                patch.data = _apply_printability_constraint(patch.data)

    # Convert to PIL Image
    result = patch.detach().cpu().squeeze(0).permute(1, 2, 0).numpy()
    result = (result * 255).clip(0, 255).astype(np.uint8)
    img = Image.fromarray(result)

    if output_path:
        img.save(output_path)
    return img


def _apply_random_transform(
    patch: "torch.Tensor",
    config: AdversarialPatchConfig,
    device: "torch.device",
) -> "torch.Tensor":
    """Apply a random affine transform + brightness for EOT."""
    import torch
    import torch.nn.functional as F

    b, c, h, w = patch.shape

    # Random rotation
    angle = random.uniform(*config.angle_range)
    angle_rad = np.radians(angle)

    # Random scale
    scale = random.uniform(*config.scale_range)

    # Build affine matrix
    cos_a = np.cos(angle_rad) * scale
    sin_a = np.sin(angle_rad) * scale
    theta = torch.tensor(
        [[cos_a, -sin_a, 0.0], [sin_a, cos_a, 0.0]],
        dtype=torch.float32,
        device=device,
    ).unsqueeze(0)

    grid = F.affine_grid(theta, patch.size(), align_corners=False)
    transformed = F.grid_sample(patch, grid, align_corners=False, padding_mode="zeros")

    # Random brightness
    brightness = random.uniform(*config.brightness_range)
    transformed = transformed * brightness

    return transformed.clamp(0.0, 1.0)


def _compute_disruption_loss(patch: "torch.Tensor", device: "torch.device") -> "torch.Tensor":
    """
    Compute a loss that encourages OCR disruption.

    Uses proxy objectives that correlate with OCR failure:
    1. High-frequency energy — creates features at character-recognition scales
    2. Edge density — mimics character strokes to confuse segmentation
    3. Spatial frequency targeting — hits the frequencies OCR models are sensitive to

    These proxy losses enable gradient-based optimization without needing a
    differentiable OCR model in the loop.
    """
    import torch

    # 1. Maximize high-frequency energy (Laplacian magnitude)
    laplacian_kernel = torch.tensor(
        [[0, 1, 0], [1, -4, 1], [0, 1, 0]],
        dtype=torch.float32, device=device,
    ).reshape(1, 1, 3, 3).expand(3, 1, 3, 3)

    edges = torch.nn.functional.conv2d(patch, laplacian_kernel, groups=3, padding=1)
    edge_loss = -edges.abs().mean()  # negative because we want to maximize

    # 2. Encourage horizontal and vertical stroke patterns (like characters)
    # Sobel-x for vertical edges (character strokes are mostly vertical)
    sobel_x = torch.tensor(
        [[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]],
        dtype=torch.float32, device=device,
    ).reshape(1, 1, 3, 3).expand(3, 1, 3, 3)
    vert_edges = torch.nn.functional.conv2d(patch, sobel_x, groups=3, padding=1)
    stroke_loss = -vert_edges.abs().mean()

    # 3. Encourage contrast — OCR needs high contrast to read characters
    # Maximize variance across spatial dimensions
    contrast_loss = -patch.var()

    # 4. Periodic structure at character-width scale
    # Characters on plates are ~30-60px wide at capture resolution
    # Encourage periodic variation at this scale via autocorrelation penalty
    shifted = torch.roll(patch, shifts=40, dims=3)
    periodicity_loss = -(patch - shifted).abs().mean()

    return edge_loss + 0.5 * stroke_loss + 0.3 * contrast_loss + 0.2 * periodicity_loss


def _total_variation(x: "torch.Tensor") -> "torch.Tensor":
    """Total variation loss for spatial smoothness."""
    tv_h = (x[:, :, 1:, :] - x[:, :, :-1, :]).abs().mean()
    tv_w = (x[:, :, :, 1:] - x[:, :, :, :-1]).abs().mean()
    return tv_h + tv_w


def _apply_printability_constraint(patch: "torch.Tensor") -> "torch.Tensor":
    """Constrain colors to CMYK-printable gamut (approximate)."""
    # Simple constraint: avoid extremely saturated colors that can't be
    # reproduced on inkjet/sticker paper
    import torch
    min_channel = patch.min(dim=1, keepdim=True).values
    max_channel = patch.max(dim=1, keepdim=True).values
    saturation = (max_channel - min_channel) / (max_channel + 1e-8)
    # Reduce saturation where it exceeds printable range
    mask = saturation > 0.95
    if mask.any():
        mean = patch.mean(dim=1, keepdim=True)
        patch = torch.where(mask.expand_as(patch), mean + (patch - mean) * 0.9, patch)
    return patch


def _generate_heuristic_patch(
    config: AdversarialPatchConfig,
    output_path: str | None = None,
) -> "Image.Image":
    """
    Fallback: generate a high-frequency pattern without gradient optimization.

    Uses known principles of OCR disruption:
    - Character-like stroke patterns at plate-font spatial frequency
    - High contrast edges that confuse segmentation
    - Periodic structure that creates phantom character boundaries
    """
    img = Image.new("RGB", (config.width, config.height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    if config.seed is not None:
        random.seed(config.seed)
        np.random.seed(config.seed)

    # Layer 1: Vertical strokes at character-width spacing (~40px)
    stroke_spacing = 40
    for x in range(0, config.width, stroke_spacing):
        # Vary stroke width to create character-like features
        w = random.randint(3, 12)
        color = random.choice([(0, 0, 0), (40, 40, 40), (80, 80, 80)])
        draw.rectangle([x, 0, x + w, config.height], fill=color)

    # Layer 2: Horizontal bars at character-height intervals
    bar_spacing = config.height // 3
    for y in range(0, config.height, bar_spacing):
        h = random.randint(2, 6)
        draw.rectangle([0, y, config.width, y + h], fill=(0, 0, 0))

    # Layer 3: Confusion characters scattered with varying opacity
    font = _load_plate_font(72)
    confusion_chars = list(CONFUSION_PAIRS.keys())
    for _ in range(12):
        ch = random.choice(confusion_chars)
        x = random.randint(0, config.width - 40)
        y = random.randint(0, config.height - 40)
        gray = random.randint(0, 120)
        draw.text((x, y), ch, fill=(gray, gray, gray), font=font)

    # Layer 4: Gaussian noise overlay for spatial frequency disruption
    arr = np.array(img, dtype=np.float32)
    noise = np.random.normal(0, 25, arr.shape)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr)

    if output_path:
        img.save(output_path)
    return img


# ═══════════════════════════════════════════════════════════════════════════
# 5. Batch Generation & Multi-Strategy Utilities
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class DecalCandidate:
    """A generated decal with metadata for evaluation."""
    image: "Image.Image"
    strategy: str
    params: dict
    path: str | None = None

    def save(self, output_path: str) -> None:
        self.image.save(output_path)
        self.path = output_path


def generate_candidate_suite(
    target_plate: str | None = None,
    output_dir: str | None = None,
    strategies: Sequence[str] | None = None,
    variants_per_strategy: int = 3,
    seed: int = 42,
) -> list[DecalCandidate]:
    """
    Generate a full suite of decal candidates across all attack strategies.

    This is the main entry point for producing a batch of decals to evaluate.
    Returns a list of DecalCandidate objects, each with its image and metadata.

    Args:
        target_plate: If provided, generates targeted attacks for this plate text
        output_dir: If provided, saves all decals to this directory
        strategies: Which strategies to use (default: all four)
        variants_per_strategy: Number of variants to generate per strategy
        seed: Random seed for reproducibility
    """
    if strategies is None:
        strategies = ["confusion", "segmentation", "ir_phantom", "adversarial_patch"]

    if output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    random.seed(seed)
    np.random.seed(seed)

    candidates: list[DecalCandidate] = []
    variant_idx = 0

    for strategy in strategies:
        for v in range(variants_per_strategy):
            current_seed = seed + variant_idx
            random.seed(current_seed)
            np.random.seed(current_seed)

            if strategy == "confusion":
                img = generate_confusion_decal(
                    config=ConfusionDecalConfig(
                        plate_mimicry=bool(v % 2),
                        font_size=random.choice([60, 72, 84]),
                    ),
                    target_plate=target_plate,
                )
            elif strategy == "segmentation":
                img = generate_segmentation_decal(
                    config=SegmentationDecalConfig(
                        extend_plate_border=True,
                        font_size=random.choice([60, 72, 84]),
                        edge_padding=random.choice([2, 4, 8]),
                    ),
                    target_plate=target_plate,
                )
            elif strategy == "ir_phantom":
                wavelength = random.choice([850, 940])
                img = generate_ir_phantom_decal(
                    config=IRPhantomConfig(
                        target_wavelength_nm=wavelength,
                        font_size=random.choice([60, 72, 84]),
                    ),
                    target_plate=target_plate,
                )
            elif strategy == "adversarial_patch":
                img = _generate_heuristic_patch(
                    AdversarialPatchConfig(seed=current_seed),
                )
            else:
                continue

            candidate = DecalCandidate(
                image=img,
                strategy=strategy,
                params={"variant": v, "seed": current_seed},
            )

            if output_dir:
                path = str(Path(output_dir) / f"{strategy}_v{v}.png")
                candidate.save(path)

            candidates.append(candidate)
            variant_idx += 1

    return candidates
