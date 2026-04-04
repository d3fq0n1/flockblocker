"""
IR camera simulation for Flock Safety LPR testing.

Simulates how scenes appear under near-infrared illumination at common
Flock camera wavelengths (850nm, 940nm).  Both plate_compositor and
decal_generator import from here so the transform stays in one place.

Physics summary
---------------
Silicon sensors respond to NIR.  Flock cameras use active IR illumination
and capture in grayscale.  Different visible-light colors collapse to
similar intensities under IR — this is the basis of the phantom-injection
attack (§3.3 in VULNERABILITY_CATALOG.md).

Weight derivation (approximate):
    850nm — Red channel dominates sensor response, blue is nearly invisible.
    940nm — Flatter response, slight red bias remains.
"""

from __future__ import annotations

import numpy as np

try:
    from PIL import Image
except ImportError:
    Image = None

# ── Wavelength-specific RGB weights ──────────────────────────────────────
# Each tuple gives (R, G, B) contribution to the grayscale IR image.

IR_WEIGHTS: dict[int, tuple[float, float, float]] = {
    850: (0.50, 0.35, 0.15),
    940: (0.40, 0.35, 0.25),
}

# Threshold: wavelengths at or below this use the 850nm profile.
_WAVELENGTH_BOUNDARY = 850


def ir_weights_for(wavelength_nm: int) -> tuple[float, float, float]:
    """Return (R, G, B) sensor-response weights for a given wavelength."""
    if wavelength_nm in IR_WEIGHTS:
        return IR_WEIGHTS[wavelength_nm]
    if wavelength_nm <= _WAVELENGTH_BOUNDARY:
        return IR_WEIGHTS[850]
    return IR_WEIGHTS[940]


def simulate_ir(
    image: "Image.Image",
    wavelength_nm: int = 850,
) -> "Image.Image":
    """
    Convert an RGB image to simulated IR-camera grayscale.

    Args:
        image: PIL RGB image.
        wavelength_nm: Target NIR wavelength (850 or 940 typical).

    Returns:
        3-channel grayscale PIL image (gray values replicated across R, G, B
        so downstream code that expects an RGB image still works).
    """
    if Image is None:
        raise ImportError("Pillow is required: pip install Pillow")

    arr = np.array(image, dtype=np.float32)
    r_w, g_w, b_w = ir_weights_for(wavelength_nm)

    gray = arr[:, :, 0] * r_w + arr[:, :, 1] * g_w + arr[:, :, 2] * b_w
    gray = np.clip(gray, 0, 255).astype(np.uint8)
    return Image.fromarray(np.stack([gray, gray, gray], axis=-1))
