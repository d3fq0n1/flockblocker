"""
Adversarial pattern generation strategies for ALPR OCR research.

Three strategies targeting documented OCR pipeline vulnerabilities:
1. Character Ambiguity — exploits OCR confusion pairs
2. Retroreflective Interference — geometric patterns for IR interaction
3. Boundary Noise — sub-perceptual noise at character edges

References:
- Song et al., "Fooling OCR Systems with Adversarial Text Images" (2022)
- Eykholt et al., "Robust Physical-World Attacks on Deep Learning Models" (CVPR 2018)
- TPAMI 2022 Adversarial Sticker methodology
"""

import hashlib
import random
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Known OCR confusion pairs — characters that degrade classifier confidence
# when rendered at boundary font weights / stroke widths.
#
# CANONICAL SOURCE: tools/decal_generator.py::CONFUSION_PAIRS
# This dict MUST remain identical to the tools/ version so that stickers
# produced by sticker_gen/ are evaluated against the same confusion model
# used by the research pipeline. Test coverage in
# tools/tests/test_decal_generator.py asserts equality — do not edit one
# without the other.
CONFUSION_PAIRS = {
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

# High-confusion character set — all chars that appear in confusion pairs
HIGH_CONFUSION_CHARS = "".join(sorted(CONFUSION_PAIRS.keys()))

# Retroreflective interference pattern parameters
# Based on documented IR interaction at 850nm/940nm wavelengths
RETRO_PATTERNS = {
    "chevron": {"angle": 45, "spacing": 8, "width": 3},
    "diamond": {"size": 12, "spacing": 16, "width": 2},
    "concentric": {"ring_spacing": 10, "width": 2},
    "crosshatch": {"angle1": 30, "angle2": -30, "spacing": 6, "width": 2},
}

# Label dimensions for Avery 5163 (2" x 4" at 300 DPI)
LABEL_WIDTH_PX = 1200  # 4 inches * 300 DPI
LABEL_HEIGHT_PX = 600  # 2 inches * 300 DPI


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Get a monospace font, falling back to default if needed."""
    font_paths = [
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeMono.ttf",
    ]
    if bold:
        bold_paths = [p for p in font_paths if "Bold" in p]
        font_paths = bold_paths + font_paths

    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def _add_research_footer(
    draw: ImageDraw.ImageDraw,
    img: Image.Image,
    footer_text: str,
) -> None:
    """Add small research attribution footer to bottom of image."""
    font = _get_font(14)
    bbox = draw.textbbox((0, 0), footer_text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (img.width - text_w) // 2
    y = img.height - text_h - 4
    # Semi-transparent background strip
    draw.rectangle(
        [0, y - 2, img.width, img.height],
        fill=(255, 255, 255, 200),
    )
    draw.text((x, y), footer_text, fill=(100, 100, 100), font=font)


def generate_character_ambiguity(
    plate_text: str,
    seed: Optional[int] = None,
    variant: int = 0,
) -> Image.Image:
    """
    Strategy A: Character Ambiguity

    Generates patterns exploiting known OCR confusion pairs (0/O, 1/I/l, 8/B,
    5/S, 2/Z) using font-weight and stroke-width manipulation at the boundary
    of human legibility vs machine classification confidence.

    The output is human-readable. Machine confidence degrades.

    Args:
        plate_text: Target plate text to generate confusion patterns for
        seed: Random seed for reproducibility
        variant: Visual variant (0=standard, 1=bold-weight, 2=mixed-weight)
    """
    from . import RESEARCH_FOOTER

    rng = random.Random(seed if seed is not None else hash(plate_text) + variant)

    img = Image.new("RGBA", (LABEL_WIDTH_PX, LABEL_HEIGHT_PX), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Generate confusion sequence from plate text
    confusion_chars = []
    for ch in plate_text.upper():
        if ch in CONFUSION_PAIRS:
            confusion_chars.append(rng.choice(CONFUSION_PAIRS[ch]))
        else:
            confusion_chars.append(rng.choice(list(HIGH_CONFUSION_CHARS)))

    # Add extra confusion characters to fill the label
    while len(confusion_chars) < len(plate_text) + 4:
        confusion_chars.append(rng.choice(list(HIGH_CONFUSION_CHARS)))

    confusion_text = "".join(confusion_chars)

    # Variant controls rendering approach
    if variant == 0:
        # Standard: uniform weight, plate-like appearance
        font_size = 96
        font = _get_font(font_size)
        # Draw plate-like border
        draw.rectangle(
            [20, 20, LABEL_WIDTH_PX - 20, LABEL_HEIGHT_PX - 80],
            outline=(0, 0, 0),
            width=3,
        )
        bbox = draw.textbbox((0, 0), confusion_text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (LABEL_WIDTH_PX - tw) // 2
        y = (LABEL_HEIGHT_PX - 80 - th) // 2
        draw.text((x, y), confusion_text, fill=(0, 0, 0), font=font)

    elif variant == 1:
        # Bold-weight: thicker strokes push characters toward confusion boundary
        font_size = 96
        font = _get_font(font_size, bold=True)
        draw.rectangle(
            [20, 20, LABEL_WIDTH_PX - 20, LABEL_HEIGHT_PX - 80],
            outline=(0, 0, 0),
            width=4,
        )
        bbox = draw.textbbox((0, 0), confusion_text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (LABEL_WIDTH_PX - tw) // 2
        y = (LABEL_HEIGHT_PX - 80 - th) // 2
        # Multi-pass rendering for weight simulation
        for dx, dy in [(0, 0), (1, 0), (0, 1), (1, 1)]:
            draw.text((x + dx, y + dy), confusion_text, fill=(0, 0, 0), font=font)

    elif variant == 2:
        # Mixed-weight: each character at different stroke width
        font_size = 88
        draw.rectangle(
            [20, 20, LABEL_WIDTH_PX - 20, LABEL_HEIGHT_PX - 80],
            outline=(0, 0, 0),
            width=3,
        )
        x_cursor = 60
        y_base = (LABEL_HEIGHT_PX - 80) // 2 - font_size // 2
        for i, ch in enumerate(confusion_text):
            is_bold = rng.random() > 0.5
            font = _get_font(font_size + rng.randint(-8, 8), bold=is_bold)
            bbox = draw.textbbox((0, 0), ch, font=font)
            ch_w = bbox[2] - bbox[0]
            if is_bold:
                for dx, dy in [(0, 0), (1, 0), (0, 1)]:
                    draw.text(
                        (x_cursor + dx, y_base + dy), ch, fill=(0, 0, 0), font=font
                    )
            else:
                draw.text((x_cursor, y_base), ch, fill=(0, 0, 0), font=font)
            x_cursor += ch_w + rng.randint(8, 20)

    _add_research_footer(draw, img, RESEARCH_FOOTER)
    return img


def generate_retroreflective(
    plate_text: str,
    seed: Optional[int] = None,
    variant: int = 0,
) -> Image.Image:
    """
    Strategy B: Retroreflective Interference

    Generates high-contrast geometric patterns calibrated for retroreflective
    substrate interaction. Designed for research documentation of how pattern
    placement affects OCR confidence scoring.

    Patterns are decorative in visible spectrum. Research documents IR interaction.

    Args:
        plate_text: Target plate text (used for pattern calibration)
        seed: Random seed for reproducibility
        variant: Pattern variant (0=chevron, 1=diamond, 2=concentric, 3=crosshatch)
    """
    from . import RESEARCH_FOOTER

    rng = random.Random(seed if seed is not None else hash(plate_text) + variant)

    img = Image.new("RGBA", (LABEL_WIDTH_PX, LABEL_HEIGHT_PX), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    arr = np.array(img)

    pattern_names = list(RETRO_PATTERNS.keys())
    pattern_name = pattern_names[variant % len(pattern_names)]
    params = RETRO_PATTERNS[pattern_name]

    # High-contrast black/white patterns optimized for retroreflective interaction
    if pattern_name == "chevron":
        spacing = params["spacing"]
        w = params["width"]
        angle = params["angle"]
        for y in range(0, LABEL_HEIGHT_PX - 40, spacing):
            for x in range(0, LABEL_WIDTH_PX, spacing):
                # Alternating chevron stripes
                offset = (x + y * np.tan(np.radians(angle))) % (spacing * 2)
                if offset < spacing:
                    x1, y1 = max(0, x), max(0, y)
                    x2 = min(LABEL_WIDTH_PX, x + w)
                    y2 = min(LABEL_HEIGHT_PX - 40, y + w)
                    draw.rectangle([x1, y1, x2, y2], fill=(0, 0, 0, 255))

    elif pattern_name == "diamond":
        size = params["size"]
        spacing = params["spacing"]
        for cy in range(size, LABEL_HEIGHT_PX - 40, spacing):
            for cx in range(size, LABEL_WIDTH_PX, spacing):
                points = [
                    (cx, cy - size // 2),
                    (cx + size // 2, cy),
                    (cx, cy + size // 2),
                    (cx - size // 2, cy),
                ]
                fill_color = (0, 0, 0, 255) if (cx + cy) % (spacing * 2) < spacing else (80, 80, 80, 255)
                draw.polygon(points, fill=fill_color)

    elif pattern_name == "concentric":
        cx, cy = LABEL_WIDTH_PX // 2, (LABEL_HEIGHT_PX - 40) // 2
        max_r = max(LABEL_WIDTH_PX, LABEL_HEIGHT_PX)
        ring_spacing = params["ring_spacing"]
        w = params["width"]
        for r in range(ring_spacing, max_r, ring_spacing):
            draw.ellipse(
                [cx - r, cy - r, cx + r, cy + r],
                outline=(0, 0, 0, 255),
                width=w,
            )

    elif pattern_name == "crosshatch":
        spacing = params["spacing"]
        w = params["width"]
        for offset in range(0, max(LABEL_WIDTH_PX, LABEL_HEIGHT_PX) * 2, spacing):
            # Diagonal lines in two directions
            draw.line(
                [(offset - LABEL_HEIGHT_PX, 0), (offset, LABEL_HEIGHT_PX - 40)],
                fill=(0, 0, 0, 255),
                width=w,
            )
            draw.line(
                [(LABEL_WIDTH_PX - offset + LABEL_HEIGHT_PX, 0),
                 (LABEL_WIDTH_PX - offset, LABEL_HEIGHT_PX - 40)],
                fill=(0, 0, 0, 255),
                width=w,
            )

    # Add subtle frequency modulation based on plate hash for pattern uniqueness
    plate_hash = int(hashlib.md5(plate_text.encode()).hexdigest()[:8], 16)
    noise_scale = 0.03
    arr = np.array(img).astype(np.float32)
    noise = rng.gauss(0, 1)
    # Subtle per-pixel modulation
    ys = np.arange(LABEL_HEIGHT_PX).reshape(-1, 1)
    xs = np.arange(LABEL_WIDTH_PX).reshape(1, -1)
    modulation = np.sin(xs * 0.05 + plate_hash * 0.001) * np.cos(ys * 0.05) * 15
    arr[:, :, :3] = np.clip(arr[:, :, :3] + modulation[:, :, np.newaxis], 0, 255)
    img = Image.fromarray(arr.astype(np.uint8), "RGBA")
    draw = ImageDraw.Draw(img)

    _add_research_footer(draw, img, RESEARCH_FOOTER)
    return img


def generate_boundary_noise(
    plate_text: str,
    seed: Optional[int] = None,
    variant: int = 0,
) -> Image.Image:
    """
    Strategy C: Boundary Noise

    Generates fine-grain noise patterns along character boundary regions that
    are below human perceptual threshold but within documented OCR confidence
    degradation ranges.

    References:
    - "Fooling OCR Systems with Adversarial Text Images" (2022)
    - TPAMI 2022 Adversarial Sticker methodology

    Args:
        plate_text: Target plate text to generate boundary noise for
        seed: Random seed for reproducibility
        variant: Noise variant (0=gaussian, 1=salt-pepper, 2=structured)
    """
    from . import RESEARCH_FOOTER

    rng_seed = seed if seed is not None else hash(plate_text) + variant
    rng = random.Random(rng_seed)
    np_rng = np.random.RandomState(rng_seed & 0xFFFFFFFF)

    img = Image.new("RGBA", (LABEL_WIDTH_PX, LABEL_HEIGHT_PX), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Render plate-like text as the base
    font = _get_font(96)
    bbox = draw.textbbox((0, 0), plate_text.upper(), font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    text_x = (LABEL_WIDTH_PX - tw) // 2
    text_y = (LABEL_HEIGHT_PX - 80 - th) // 2

    # Draw the text
    draw.text((text_x, text_y), plate_text.upper(), fill=(0, 0, 0), font=font)

    # Convert to array for noise application
    arr = np.array(img).astype(np.float32)

    # Detect character boundaries using gradient magnitude
    gray = arr[:, :, 0]  # Use red channel as proxy
    # Sobel-like edge detection
    gy = np.abs(np.diff(gray, axis=0, prepend=gray[:1, :]))
    gx = np.abs(np.diff(gray, axis=1, prepend=gray[:, :1]))
    edges = np.sqrt(gx**2 + gy**2)
    # Dilate edges to get boundary region
    from PIL import ImageFilter

    edge_img = Image.fromarray(np.clip(edges, 0, 255).astype(np.uint8))
    edge_img = edge_img.filter(ImageFilter.MaxFilter(size=7))
    edge_mask = np.array(edge_img).astype(np.float32) / 255.0

    if variant == 0:
        # Gaussian noise concentrated at boundaries
        noise = np_rng.normal(0, 25, arr[:, :, :3].shape)
        noise *= edge_mask[:, :, np.newaxis]
        arr[:, :, :3] = np.clip(arr[:, :, :3] + noise, 0, 255)

    elif variant == 1:
        # Salt-and-pepper noise at boundary regions
        sp_mask = np_rng.random(gray.shape) * edge_mask
        # Salt
        arr[:, :, :3][sp_mask > 0.85] = 255
        # Pepper
        arr[:, :, :3][sp_mask < 0.05] = np.where(
            edge_mask[sp_mask < 0.05, np.newaxis] > 0.1, 0, arr[:, :, :3][sp_mask < 0.05]
        ) if edge_mask[sp_mask < 0.05].any() else arr[:, :, :3][sp_mask < 0.05]
        salt_pts = sp_mask > 0.85
        pepper_pts = (sp_mask < 0.15) & (sp_mask > 0) & (edge_mask > 0.1)
        arr[salt_pts, :3] = 255
        arr[pepper_pts, :3] = 0

    elif variant == 2:
        # Structured noise — periodic perturbation at character edges
        ys = np.arange(LABEL_HEIGHT_PX).reshape(-1, 1)
        xs = np.arange(LABEL_WIDTH_PX).reshape(1, -1)
        freq = 0.3 + variant * 0.1
        structured = np.sin(xs * freq) * np.cos(ys * freq * 0.7) * 30
        structured *= edge_mask
        arr[:, :, :3] = np.clip(
            arr[:, :, :3] + structured[:, :, np.newaxis], 0, 255
        )

    # Add subtle global noise floor (below perceptual threshold)
    global_noise = np_rng.normal(0, 3, arr[:, :, :3].shape)
    arr[:, :, :3] = np.clip(arr[:, :, :3] + global_noise, 0, 255)

    img = Image.fromarray(arr.astype(np.uint8), "RGBA")
    draw = ImageDraw.Draw(img)

    # Plate-like border
    draw.rectangle(
        [20, 20, LABEL_WIDTH_PX - 20, LABEL_HEIGHT_PX - 80],
        outline=(0, 0, 0),
        width=2,
    )

    _add_research_footer(draw, img, RESEARCH_FOOTER)
    return img


# Strategy registry
STRATEGIES = {
    "character_ambiguity": generate_character_ambiguity,
    "retroreflective": generate_retroreflective,
    "boundary_noise": generate_boundary_noise,
}

STRATEGY_DESCRIPTIONS = {
    "character_ambiguity": "OCR confusion pair exploitation (0/O, 1/I, 8/B, 5/S, 2/Z)",
    "retroreflective": "High-contrast geometric patterns for retroreflective interaction",
    "boundary_noise": "Sub-perceptual noise at character boundary regions",
}
