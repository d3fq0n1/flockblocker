"""
Composite plate + decal images for testing.

Simulates how a Flock camera would see a plate with a nearby decal/sticker
under various conditions (distance, angle, perspective, IR simulation).
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ir_simulation import simulate_ir

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = None


@dataclass
class CompositeConfig:
    """Configuration for plate + decal composite generation.

    Set ``decal_gap_px`` to a negative value to overlap the decal with the
    plate.  This simulates a bumper sticker partially tucked under or
    pressed against the plate edge, pushing phantom characters into the
    plate segmentation zone.  The plate is always composited on top so its
    text remains unobscured.

    Perspective simulation
    ~~~~~~~~~~~~~~~~~~~~~~
    ``yaw_deg`` models horizontal camera offset (roadside-mounted cameras
    viewing a vehicle at an angle).  ``pitch_deg`` models vertical offset
    (pole-mounted cameras looking down at the plate).  Both use a 3D
    perspective projection mapped to a 2D homography.

    Legacy ``angle_deg`` is aliased to ``yaw_deg`` for backward compatibility.
    """
    # Decal placement relative to plate
    decal_position: str = "below"  # above, below, left, right
    decal_gap_px: int = 10         # gap in px; negative = overlap

    # Simulated capture conditions
    distance_ft: float = 25.0      # simulated capture distance
    angle_deg: float = 0.0         # horizontal angle offset (legacy alias for yaw_deg)
    yaw_deg: float = 0.0           # horizontal camera offset (roadside mount)
    pitch_deg: float = 0.0         # vertical camera offset (pole mount, looking down)
    motion_blur_px: int = 0        # motion blur kernel size

    # IR simulation
    simulate_ir: bool = False      # convert to IR-like grayscale
    ir_wavelength_nm: int = 850    # 850nm or 940nm (common Flock wavelengths)

    # Image output
    output_width: int = 640
    output_height: int = 480

    @property
    def effective_yaw(self) -> float:
        """Resolve yaw from explicit yaw_deg or legacy angle_deg."""
        if self.yaw_deg != 0.0:
            return self.yaw_deg
        return self.angle_deg


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

    # Calculate composite canvas size.
    # Negative gap = overlap; canvas shrinks but both images still fit.
    gap = config.decal_gap_px
    if config.decal_position in ("above", "below"):
        canvas_w = max(plate.width, decal.width)
        canvas_h = plate.height + gap + decal.height
    else:
        canvas_w = plate.width + gap + decal.width
        canvas_h = max(plate.height, decal.height)

    # Clamp canvas to at least plate size (extreme overlap)
    canvas_w = max(canvas_w, plate.width)
    canvas_h = max(canvas_h, plate.height)

    canvas = Image.new("RGB", (canvas_w, canvas_h), color=(40, 40, 40))

    # Place plate and decal.
    # With negative gap the decal slides under the plate edge.
    # Paste decal first, then plate on top — plate text stays unobscured.
    if config.decal_position == "below":
        plate_x = (canvas_w - plate.width) // 2
        plate_y = 0
        decal_x = (canvas_w - decal.width) // 2
        decal_y = plate.height + gap
    elif config.decal_position == "above":
        decal_x = (canvas_w - decal.width) // 2
        decal_y = 0
        plate_x = (canvas_w - plate.width) // 2
        plate_y = decal.height + gap
    elif config.decal_position == "left":
        decal_x = 0
        decal_y = (canvas_h - decal.height) // 2
        plate_x = decal.width + gap
        plate_y = (canvas_h - plate.height) // 2
    else:  # right
        plate_x = 0
        plate_y = (canvas_h - plate.height) // 2
        decal_x = plate.width + gap
        decal_y = (canvas_h - decal.height) // 2

    # Decal first (behind), then plate on top
    canvas.paste(decal, (decal_x, decal_y))
    canvas.paste(plate, (plate_x, plate_y))

    # Apply perspective warp (yaw + pitch)
    yaw = config.effective_yaw
    pitch = config.pitch_deg
    if yaw != 0.0 or pitch != 0.0:
        canvas = _apply_perspective_warp(canvas, yaw, pitch)

    # Simulate IR capture
    if config.simulate_ir:
        canvas = simulate_ir(canvas, config.ir_wavelength_nm)

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



def _apply_perspective_warp(
    image: "Image.Image",
    yaw_deg: float,
    pitch_deg: float,
) -> "Image.Image":
    """Apply perspective warp simulating camera viewing angle.

    Models a 3D perspective projection where the camera is offset
    horizontally (yaw) and/or vertically (pitch) from the plate's
    normal axis.  The result is a foreshortened image — one side
    appears compressed, the other expanded — matching what a
    roadside or pole-mounted Flock camera actually sees.

    The approach:
    1. Define the plate as a rectangle in 3D space (Z=0 plane)
    2. Place a virtual camera at a known distance, offset by yaw/pitch
    3. Project the 4 corners through the camera model
    4. Compute the homography from original corners to projected corners
    5. Apply via PIL's ``transform(PERSPECTIVE)``

    Args:
        image: Source PIL image.
        yaw_deg: Horizontal angle in degrees. Positive = camera is to the
                 right of the plate normal (left side of plate appears
                 foreshortened).
        pitch_deg: Vertical angle in degrees. Positive = camera is above
                   the plate (top of plate appears foreshortened / plate
                   tilts away at top).

    Returns:
        Warped PIL image with same dimensions as input.
    """
    w, h = image.size

    # Convert to radians
    yaw = np.radians(yaw_deg)
    pitch = np.radians(pitch_deg)

    # Virtual camera distance (in pixel units).  Larger = less extreme
    # perspective for a given angle.  Calibrated so 15° gives noticeable
    # but realistic foreshortening at typical Flock capture distances.
    focal_length = max(w, h) * 2.0

    # Define plate corners in 3D (centered at origin, Z=0)
    hw, hh = w / 2.0, h / 2.0
    corners_3d = np.array([
        [-hw, -hh, 0],  # top-left
        [ hw, -hh, 0],  # top-right
        [ hw,  hh, 0],  # bottom-right
        [-hw,  hh, 0],  # bottom-left
    ], dtype=np.float64)

    # Camera rotation matrix: Ry(yaw) @ Rx(pitch)
    # Yaw rotates around Y axis, pitch rotates around X axis
    cy, sy = np.cos(yaw), np.sin(yaw)
    cp, sp = np.cos(pitch), np.sin(pitch)

    R_yaw = np.array([
        [ cy, 0, sy],
        [  0, 1,  0],
        [-sy, 0, cy],
    ])
    R_pitch = np.array([
        [1,  0,   0],
        [0,  cp, -sp],
        [0,  sp,  cp],
    ])
    R = R_yaw @ R_pitch

    # Camera position: looking from distance along Z axis, rotated
    # We keep the camera at (0, 0, focal_length) and rotate the plate instead
    # This is equivalent and simpler to compute
    rotated = (R @ corners_3d.T).T

    # Translate so plate is at Z = focal_length (in front of camera)
    rotated[:, 2] += focal_length

    # Perspective projection: (x, y) = f * (X/Z, Y/Z)
    projected = np.zeros((4, 2), dtype=np.float64)
    for i in range(4):
        z = rotated[i, 2]
        if z <= 0:
            z = 0.1  # clamp to avoid division by zero for extreme angles
        projected[i, 0] = focal_length * rotated[i, 0] / z + hw
        projected[i, 1] = focal_length * rotated[i, 1] / z + hh

    # Source corners (original image)
    src = np.array([
        [0, 0],
        [w, 0],
        [w, h],
        [0, h],
    ], dtype=np.float64)

    # Compute 3x3 perspective transform matrix from src → projected
    coeffs = _find_perspective_coeffs(projected, src)

    return image.transform(
        (w, h),
        Image.PERSPECTIVE,
        coeffs,
        Image.BICUBIC,
        fillcolor=(40, 40, 40),  # match canvas background
    )


def _find_perspective_coeffs(
    dst: np.ndarray,
    src: np.ndarray,
) -> tuple:
    """Compute the 8 perspective transform coefficients for PIL.

    Given 4 source points and 4 destination points, solves the system:
        x' = (a*x + b*y + c) / (g*x + h*y + 1)
        y' = (d*x + e*y + f) / (g*x + h*y + 1)

    PIL's Image.transform(PERSPECTIVE) expects coefficients (a,b,c,d,e,f,g,h)
    that map *destination* to *source* (inverse mapping), so we solve for
    the transform that maps dst→src.

    Args:
        dst: 4x2 array of destination points.
        src: 4x2 array of source points.

    Returns:
        Tuple of 8 floats (a, b, c, d, e, f, g, h).
    """
    # Build the 8x8 linear system
    A = np.zeros((8, 8))
    b = np.zeros(8)

    for i in range(4):
        x, y = dst[i]
        X, Y = src[i]
        A[2 * i] = [x, y, 1, 0, 0, 0, -X * x, -X * y]
        A[2 * i + 1] = [0, 0, 0, x, y, 1, -Y * x, -Y * y]
        b[2 * i] = X
        b[2 * i + 1] = Y

    coeffs = np.linalg.solve(A, b)
    return tuple(coeffs)


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
