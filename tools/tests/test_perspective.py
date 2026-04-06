"""Tests for perspective warp in plate compositor."""

import tempfile
from pathlib import Path

import numpy as np
import pytest

from plate_compositor import (
    CompositeConfig,
    create_composite,
    generate_test_plate,
    _apply_perspective_warp,
    _find_perspective_coeffs,
)

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


pytestmark = pytest.mark.skipif(not HAS_PIL, reason="Pillow required")


# ═══════════════════════════════════════════════════════════════════════════
# Perspective coefficient computation
# ═══════════════════════════════════════════════════════════════════════════

class TestPerspectiveCoeffs:
    def test_identity_transform(self):
        """Zero angle should produce near-identity mapping."""
        src = np.array([[0, 0], [100, 0], [100, 100], [0, 100]], dtype=np.float64)
        # With identity, dst ≈ src
        coeffs = _find_perspective_coeffs(src, src)
        # a≈1, b≈0, c≈0, d≈0, e≈1, f≈0, g≈0, h≈0
        assert abs(coeffs[0] - 1.0) < 0.01
        assert abs(coeffs[4] - 1.0) < 0.01
        assert abs(coeffs[1]) < 0.01
        assert abs(coeffs[3]) < 0.01

    def test_coefficients_length(self):
        """Should return exactly 8 coefficients."""
        src = np.array([[0, 0], [100, 0], [100, 50], [0, 50]], dtype=np.float64)
        dst = np.array([[10, 5], [90, 0], [95, 50], [5, 45]], dtype=np.float64)
        coeffs = _find_perspective_coeffs(dst, src)
        assert len(coeffs) == 8


# ═══════════════════════════════════════════════════════════════════════════
# Perspective warp function
# ═══════════════════════════════════════════════════════════════════════════

class TestPerspectiveWarp:
    def test_zero_angle_preserves_image(self):
        """Zero yaw and pitch should produce minimal change."""
        img = Image.new("RGB", (200, 100), (255, 255, 255))
        result = _apply_perspective_warp(img, 0.0, 0.0)
        assert result.size == img.size
        # Pixel values should be very close to original
        orig_arr = np.array(img)
        res_arr = np.array(result)
        assert np.allclose(orig_arr, res_arr, atol=5)

    def test_yaw_changes_image(self):
        """Non-zero yaw should produce visible foreshortening."""
        img = Image.new("RGB", (200, 100), (255, 255, 255))
        # Draw a vertical line in the center
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        draw.line([(100, 0), (100, 99)], fill=(0, 0, 0), width=3)

        original = np.array(img)
        warped = np.array(_apply_perspective_warp(img, 15.0, 0.0))

        # The images should differ
        assert not np.array_equal(original, warped)

    def test_pitch_changes_image(self):
        """Non-zero pitch should produce visible change."""
        img = Image.new("RGB", (200, 100), (255, 255, 255))
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        draw.line([(0, 50), (199, 50)], fill=(0, 0, 0), width=3)

        original = np.array(img)
        warped = np.array(_apply_perspective_warp(img, 0.0, 10.0))
        assert not np.array_equal(original, warped)

    def test_combined_yaw_pitch(self):
        """Combined yaw + pitch should work without errors."""
        img = generate_test_plate("ABC1234")
        result = _apply_perspective_warp(img, 12.0, 8.0)
        assert result.size == img.size

    def test_negative_angles(self):
        """Negative angles should work (mirror direction)."""
        img = generate_test_plate("ABC1234")
        result_pos = _apply_perspective_warp(img, 15.0, 0.0)
        result_neg = _apply_perspective_warp(img, -15.0, 0.0)
        # They should be different (mirrored foreshortening)
        assert not np.array_equal(np.array(result_pos), np.array(result_neg))

    def test_extreme_angle_no_crash(self):
        """Large angles shouldn't crash (just produce extreme warp)."""
        img = generate_test_plate("XYZ9999")
        result = _apply_perspective_warp(img, 30.0, 25.0)
        assert result.size == img.size

    def test_preserves_dimensions(self):
        """Output should have same dimensions as input."""
        for w, h in [(640, 480), (200, 100), (800, 600)]:
            img = Image.new("RGB", (w, h), (128, 128, 128))
            result = _apply_perspective_warp(img, 10.0, 5.0)
            assert result.size == (w, h)


# ═══════════════════════════════════════════════════════════════════════════
# Integration with CompositeConfig
# ═══════════════════════════════════════════════════════════════════════════

class TestCompositeConfigPerspective:
    def test_effective_yaw_from_yaw_deg(self):
        config = CompositeConfig(yaw_deg=15.0)
        assert config.effective_yaw == 15.0

    def test_effective_yaw_from_legacy_angle_deg(self):
        config = CompositeConfig(angle_deg=10.0)
        assert config.effective_yaw == 10.0

    def test_yaw_deg_takes_precedence(self):
        config = CompositeConfig(angle_deg=10.0, yaw_deg=20.0)
        assert config.effective_yaw == 20.0

    def test_composite_with_perspective(self):
        """Full composite pipeline with perspective warp."""
        with tempfile.TemporaryDirectory() as tmp:
            plate_path = str(Path(tmp) / "plate.png")
            generate_test_plate("ABC1234", output_path=plate_path)

            # Create a simple decal
            decal = Image.new("RGB", (480, 120), (200, 50, 50))
            decal_path = str(Path(tmp) / "decal.png")
            decal.save(decal_path)

            output_path = str(Path(tmp) / "composite.png")

            config = CompositeConfig(
                yaw_deg=12.0,
                pitch_deg=5.0,
                distance_ft=25.0,
            )

            result = create_composite(
                plate_path, decal_path, config, output_path
            )
            assert result.shape[2] == 3  # RGB
            assert Path(output_path).exists()

    def test_composite_no_perspective(self):
        """Composite without perspective (backward compat)."""
        with tempfile.TemporaryDirectory() as tmp:
            plate_path = str(Path(tmp) / "plate.png")
            generate_test_plate("XYZ5678", output_path=plate_path)

            decal = Image.new("RGB", (480, 120), (50, 50, 200))
            decal_path = str(Path(tmp) / "decal.png")
            decal.save(decal_path)

            config = CompositeConfig()  # defaults: 0 yaw, 0 pitch
            result = create_composite(plate_path, decal_path, config)
            assert result.shape[2] == 3
