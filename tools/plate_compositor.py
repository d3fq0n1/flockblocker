"""
Composite plate + decal images for testing.

Simulates how a Flock camera would see a plate with a nearby decal/sticker
under various conditions (distance, angle, IR simulation).
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = None


@dataclass
class CompositeConfig:
    """Configuration for plate + decal composite generation."""
    # Decal placement relative to plate
    decal_position: str = "below"  # above, below, left, right
    decal_gap_px: int = 10         # gap between plate and decal in pixels

    # Simulated capture conditions
    distance_ft: float = 25.0      # simulated capture distance
    angle_deg: float = 0.0         # horizontal angle offset
    motion_blur_px: int = 0        # motion blur kernel size

    # IR simulation
    simulate_ir: bool = False      # convert to IR-like grayscale
    ir_wavelength_nm: int = 850    # 850nm or 940nm (common Flock wavelengths)

    # Image output
    output_width: int = 640
    output_height: int = 480


def create_composite(
    plate_image_path: str,
    decal_image_path: str,
    config: CompositeConfig | None = None,
    output_path: str | None = None,
) -> np.ndarray:
    """
    Create a composite image of plate + decal as a Flock camera would capture it.

    Args:
        plate_image_path: Path to plate image
        decal_image_path: Path to decal/sticker image
        config: Composite configuration
        output_path: If provided, save composite to this path

    Returns:
        Composite image as numpy array (H, W, C)
    """
    if Image is None:
        raise ImportError("Pillow is required: pip install Pillow")

    config = config or CompositeConfig()

    plate = Image.open(plate_image_path).convert("RGB")
    decal = Image.open(decal_image_path).convert("RGB")

    # Scale decal relative to plate width
    decal_width = int(plate.width * 0.8)
    decal_height = int(decal.height * (decal_width / decal.width))
    decal = decal.resize((decal_width, decal_height), Image.LANCZOS)

    # Calculate composite canvas size
    if config.decal_position in ("above", "below"):
        canvas_w = max(plate.width, decal.width)
        canvas_h = plate.height + config.decal_gap_px + decal.height
    else:
        canvas_w = plate.width + config.decal_gap_px + decal.width
        canvas_h = max(plate.height, decal.height)

    canvas = Image.new("RGB", (canvas_w, canvas_h), color=(40, 40, 40))

    # Place plate and decal
    if config.decal_position == "below":
        plate_x = (canvas_w - plate.width) // 2
        plate_y = 0
        decal_x = (canvas_w - decal.width) // 2
        decal_y = plate.height + config.decal_gap_px
    elif config.decal_position == "above":
        decal_x = (canvas_w - decal.width) // 2
        decal_y = 0
        plate_x = (canvas_w - plate.width) // 2
        plate_y = decal.height + config.decal_gap_px
    elif config.decal_position == "left":
        decal_x = 0
        decal_y = (canvas_h - decal.height) // 2
        plate_x = decal.width + config.decal_gap_px
        plate_y = (canvas_h - plate.height) // 2
    else:  # right
        plate_x = 0
        plate_y = (canvas_h - plate.height) // 2
        decal_x = plate.width + config.decal_gap_px
        decal_y = (canvas_h - decal.height) // 2

    canvas.paste(plate, (plate_x, plate_y))
    canvas.paste(decal, (decal_x, decal_y))

    # Simulate IR capture
    if config.simulate_ir:
        canvas = _simulate_ir(canvas, config.ir_wavelength_nm)

    # Simulate distance (downscale then upscale to lose detail)
    if config.distance_ft > 15:
        scale_factor = 15.0 / config.distance_ft
        small_size = (
            max(1, int(canvas.width * scale_factor)),
            max(1, int(canvas.height * scale_factor)),
        )
        canvas = canvas.resize(small_size, Image.LANCZOS)
        canvas = canvas.resize((canvas_w, canvas_h), Image.LANCZOS)

    # Simulate motion blur
    if config.motion_blur_px > 0:
        canvas = _apply_motion_blur(canvas, config.motion_blur_px)

    if output_path:
        canvas.save(output_path)

    return np.array(canvas)


def _simulate_ir(image: "Image.Image", wavelength_nm: int) -> "Image.Image":
    """
    Simulate IR camera capture by converting to weighted grayscale.

    Different wavelengths see colors differently:
    - 850nm: red and black appear similar, greens are mid-gray
    - 940nm: even less color differentiation
    """
    arr = np.array(image, dtype=np.float32)

    if wavelength_nm <= 850:
        # At 850nm, red channel dominates, blue is nearly invisible
        weights = np.array([0.15, 0.35, 0.50])  # B, G, R in PIL RGB order
    else:
        # At 940nm, very flat response
        weights = np.array([0.25, 0.35, 0.40])

    # Note: PIL RGB order is R, G, B
    gray = arr[:, :, 0] * weights[2] + arr[:, :, 1] * weights[1] + arr[:, :, 2] * weights[0]
    gray = np.clip(gray, 0, 255).astype(np.uint8)
    return Image.fromarray(np.stack([gray, gray, gray], axis=-1))


def _apply_motion_blur(image: "Image.Image", kernel_size: int) -> "Image.Image":
    """Apply horizontal motion blur to simulate vehicle movement."""
    arr = np.array(image, dtype=np.float32)
    kernel = np.zeros((kernel_size, kernel_size))
    kernel[kernel_size // 2, :] = 1.0 / kernel_size

    from scipy.signal import convolve2d

    result = np.stack(
        [convolve2d(arr[:, :, c], kernel, mode="same", boundary="symm") for c in range(3)],
        axis=-1,
    )
    return Image.fromarray(np.clip(result, 0, 255).astype(np.uint8))


def generate_test_plate(
    plate_text: str = "ABC1234",
    state: str = "WI",
    output_path: str | None = None,
) -> "Image.Image":
    """Generate a synthetic plate image for testing."""
    if Image is None:
        raise ImportError("Pillow is required: pip install Pillow")

    # Standard US plate aspect ratio ~2:1
    width, height = 600, 300
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Border
    draw.rectangle([5, 5, width - 6, height - 6], outline=(0, 0, 0), width=3)

    # State text (top)
    try:
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
    except (OSError, IOError):
        font_small = ImageFont.load_default()
        font_large = ImageFont.load_default()

    # State label
    bbox = draw.textbbox((0, 0), state, font=font_small)
    state_w = bbox[2] - bbox[0]
    draw.text(((width - state_w) // 2, 15), state, fill=(0, 0, 100), font=font_small)

    # Plate number
    bbox = draw.textbbox((0, 0), plate_text, font=font_large)
    text_w = bbox[2] - bbox[0]
    draw.text(((width - text_w) // 2, 90), plate_text, fill=(0, 0, 0), font=font_large)

    if output_path:
        img.save(output_path)

    return img
