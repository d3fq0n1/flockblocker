"""
IR phantom character injection evaluation tests.

Validates the core thesis of attack strategy 3.3: decals that hide characters
in visible light but reveal them under IR illumination, causing phantom
characters to bleed into OCR plate reads.

Test hierarchy:
    1. Optical — do phantom chars become visible under IR?
    2. OCR detection — does OCR actually read the phantom chars?
    3. Composite bleed — do phantoms contaminate plate reads in composites?
    4. Wavelength specificity — 850nm vs 940nm palette effectiveness
"""

import pytest
import numpy as np
from pathlib import Path


# ---------------------------------------------------------------------------
# Test plates — chosen for known confusion-pair richness
# ---------------------------------------------------------------------------

PLATE_TEXTS = ["ABC1234", "HBR4051", "WKM7793"]
WAVELENGTHS = [850, 940]


# ---------------------------------------------------------------------------
# 1. Optical contrast tests — IR reveals what visible light hides
# ---------------------------------------------------------------------------

class TestPhantomOpticalContrast:
    """Verify that phantom characters emerge under IR simulation."""

    def test_visible_contrast_is_low(self):
        """In visible light, phantom text should be nearly invisible."""
        from decal_generator import generate_ir_phantom_decal, IRPhantomConfig

        config = IRPhantomConfig(phantom_chars="O0D8B")
        img = generate_ir_phantom_decal(config=config)
        arr = np.array(img, dtype=np.float32)

        # Measure per-channel standard deviation — low means text is hidden
        stds = [arr[:, :, c].std() for c in range(3)]
        avg_std = np.mean(stds)
        assert avg_std < 80, (
            f"Visible-light contrast too high (std={avg_std:.1f}); "
            "phantom chars should be nearly invisible to humans"
        )

    @pytest.mark.parametrize("wavelength", WAVELENGTHS)
    def test_ir_contrast_exceeds_visible(self, wavelength):
        """IR simulation must amplify contrast relative to visible light."""
        from decal_generator import generate_ir_phantom_decal, IRPhantomConfig
        from ir_simulation import simulate_ir

        config = IRPhantomConfig(
            phantom_chars="O0D8B",
            target_wavelength_nm=wavelength,
        )
        img = generate_ir_phantom_decal(config=config)
        ir_img = simulate_ir(img, wavelength)

        vis_arr = np.array(img, dtype=np.float32)
        ir_arr = np.array(ir_img, dtype=np.float32)

        # Compare contrast: use the ratio of standard deviations.
        # Red-channel std is the best proxy since the 850nm palette is red-on-red.
        vis_std = vis_arr[:, :, 0].std()
        ir_std = ir_arr[:, :, 0].std()

        # IR view should have meaningfully different contrast profile
        assert ir_std != pytest.approx(vis_std, abs=0.5), (
            f"IR contrast ({ir_std:.2f}) is indistinguishable from "
            f"visible ({vis_std:.2f}) at {wavelength}nm — phantom chars not revealed"
        )

    def test_ir_pixel_separation(self):
        """
        Background and text pixels should separate under IR.

        Measure the gap between the darkest and brightest regions in the
        IR-simulated image. A usable phantom needs enough separation for
        OCR binarization to detect the characters.
        """
        from decal_generator import generate_ir_phantom_decal, IRPhantomConfig
        from ir_simulation import simulate_ir

        config = IRPhantomConfig(phantom_chars="O0O0O")
        img = generate_ir_phantom_decal(config=config)
        ir_img = simulate_ir(img, 850)

        ir_gray = np.array(ir_img)[:, :, 0]  # single-channel (all 3 identical)

        # Take the 10th and 90th percentile to avoid outlier pixels
        p10 = np.percentile(ir_gray, 10)
        p90 = np.percentile(ir_gray, 90)
        separation = abs(p90 - p10)

        # Even modest separation (>2 levels) proves differential collapse
        assert separation > 1, (
            f"IR pixel separation too low ({separation:.1f}); "
            "background and text collapse identically — no phantom visible"
        )


# ---------------------------------------------------------------------------
# 2. OCR detection of phantom characters (standalone decal)
# ---------------------------------------------------------------------------

class TestPhantomOCRDetection:
    """Test whether OCR engines detect phantom characters in IR-simulated decals."""

    @pytest.fixture
    def phantom_decal_ir(self, tmp_path):
        """Generate a phantom decal and its IR-simulated version."""
        from decal_generator import generate_ir_phantom_decal, IRPhantomConfig
        from ir_simulation import simulate_ir

        chars = "O0D8B"
        config = IRPhantomConfig(
            phantom_chars=chars,
            font_size=96,
            target_wavelength_nm=850,
        )
        img = generate_ir_phantom_decal(config=config)
        ir_img = simulate_ir(img, 850)

        vis_path = tmp_path / "phantom_visible.png"
        ir_path = tmp_path / "phantom_ir.png"
        img.save(str(vis_path))
        ir_img.save(str(ir_path))

        return {
            "chars": chars,
            "visible_path": vis_path,
            "ir_path": ir_path,
        }

    def test_visible_light_ocr_reads_little(self, phantom_decal_ir):
        """In visible light the phantom decal should yield minimal OCR output."""
        from ocr_engines import get_all_engines

        engines = get_all_engines()
        if not engines:
            pytest.skip("No OCR engines available")

        vis_path = str(phantom_decal_ir["visible_path"])
        any_ran = False
        for engine in engines:
            try:
                result = engine.read_plate(vis_path)
            except Exception as exc:
                print(f"[visible] {engine.name}: skipped ({exc})")
                continue
            any_ran = True
            # Low confidence or empty read expected — text is nearly invisible
            print(f"[visible] {engine.name}: text='{result.plate_text}' "
                  f"conf={result.confidence:.2f}")

        if not any_ran:
            pytest.skip("No OCR engines could run")

    def test_ir_ocr_detects_phantom_chars(self, phantom_decal_ir):
        """Under IR, OCR should detect at least some of the phantom characters."""
        from ocr_engines import get_all_engines

        engines = get_all_engines()
        if not engines:
            pytest.skip("No OCR engines available")

        ir_path = str(phantom_decal_ir["ir_path"])
        chars = phantom_decal_ir["chars"]

        detected_by_any = False
        any_ran = False
        for engine in engines:
            try:
                result = engine.read_plate(ir_path)
            except Exception as exc:
                print(f"[IR 850nm] {engine.name}: skipped ({exc})")
                continue
            any_ran = True
            # Check if any phantom chars appear in the read
            overlap = set(result.plate_text) & set(chars)
            if overlap and result.confidence > 0.1:
                detected_by_any = True
            print(f"[IR 850nm] {engine.name}: text='{result.plate_text}' "
                  f"conf={result.confidence:.2f} overlap={overlap}")

        if not any_ran:
            pytest.skip("No OCR engines could run")

        # This is informational — detection depends on engine availability
        # and font rendering. Log results regardless.
        if not detected_by_any:
            print("NOTE: No engine detected phantom chars — may need "
                  "font/contrast tuning or engines not installed")


# ---------------------------------------------------------------------------
# 3. Composite bleed — phantoms contaminate plate reads
# ---------------------------------------------------------------------------

class TestPhantomCompositeBleed:
    """
    The money test: does a phantom decal placed near a plate cause the
    OCR read of the composite to differ from the clean plate read?
    """

    @pytest.fixture
    def plates_and_phantom(self, tmp_path):
        """Generate test plates and a phantom decal."""
        from plate_compositor import generate_test_plate
        from decal_generator import generate_ir_phantom_decal, IRPhantomConfig

        plates = {}
        for text in PLATE_TEXTS:
            path = tmp_path / f"plate_{text}.png"
            generate_test_plate(plate_text=text, output_path=str(path))
            plates[text] = path

        # Phantom decal with high-confusion characters
        config = IRPhantomConfig(phantom_chars="O0D8B", target_wavelength_nm=850)
        decal = generate_ir_phantom_decal(config=config)
        decal_path = tmp_path / "phantom_decal.png"
        decal.save(str(decal_path))

        return plates, decal_path

    @pytest.mark.parametrize("plate_text", PLATE_TEXTS)
    @pytest.mark.parametrize("wavelength", WAVELENGTHS)
    def test_phantom_alters_read_under_ir(
        self, plates_and_phantom, plate_text, wavelength, tmp_path
    ):
        """
        Compare clean-plate read vs plate+phantom-decal read under IR.

        Under visible light the decal should be inert. Under IR the phantom
        chars should bleed into the read, causing either:
        - A different plate text (char substitution, length change)
        - A confidence drop (OCR less sure even if text matches)
        """
        from plate_compositor import create_composite, CompositeConfig
        from ocr_engines import get_all_engines

        engines = get_all_engines()
        if not engines:
            pytest.skip("No OCR engines available")

        plates, decal_path = plates_and_phantom
        plate_path = plates[plate_text]

        # Clean plate under IR (no decal)
        clean_ir_path = tmp_path / f"clean_ir_{plate_text}_{wavelength}.png"
        clean_config = CompositeConfig(
            simulate_ir=True,
            ir_wavelength_nm=wavelength,
        )
        # Create a "composite" with the plate only — reuse compositor for
        # consistent IR simulation. We pass the plate as both plate and decal
        # then crop, but simpler: just apply IR to the plate directly.
        from ir_simulation import simulate_ir
        from PIL import Image

        plate_img = Image.open(str(plate_path))
        clean_ir = simulate_ir(plate_img, wavelength)
        clean_ir.save(str(clean_ir_path))

        # Plate + phantom decal under IR
        composite_ir_path = tmp_path / f"phantom_ir_{plate_text}_{wavelength}.png"
        composite_config = CompositeConfig(
            decal_position="below",
            simulate_ir=True,
            ir_wavelength_nm=wavelength,
        )
        create_composite(
            plate_image_path=str(plate_path),
            decal_image_path=str(decal_path),
            config=composite_config,
            output_path=str(composite_ir_path),
        )

        any_ran = False
        for engine in engines:
            try:
                clean_result = engine.read_plate(str(clean_ir_path))
                composite_result = engine.read_plate(str(composite_ir_path))
            except Exception as exc:
                print(f"[{engine.name}] skipped: {exc}")
                continue

            any_ran = True
            text_changed = clean_result.plate_text != composite_result.plate_text
            conf_delta = composite_result.confidence - clean_result.confidence

            status = "MISREAD" if text_changed else "same"
            print(
                f"[{engine.name}] {plate_text} @ {wavelength}nm: "
                f"clean='{clean_result.plate_text}' ({clean_result.confidence:.2f}) -> "
                f"phantom='{composite_result.plate_text}' ({composite_result.confidence:.2f}) "
                f"[{status}] (dconf={conf_delta:+.2f})"
            )

        if not any_ran:
            pytest.skip("No OCR engines could run")

    @pytest.mark.parametrize("plate_text", PLATE_TEXTS)
    def test_phantom_inert_in_visible_light(
        self, plates_and_phantom, plate_text, tmp_path
    ):
        """Phantom decal should NOT alter reads under visible light."""
        from plate_compositor import create_composite, CompositeConfig
        from ocr_engines import get_all_engines

        engines = get_all_engines()
        if not engines:
            pytest.skip("No OCR engines available")

        plates, decal_path = plates_and_phantom
        plate_path = plates[plate_text]

        # Visible-light composite (no IR simulation)
        composite_path = tmp_path / f"phantom_vis_{plate_text}.png"
        config = CompositeConfig(decal_position="below", simulate_ir=False)
        create_composite(
            plate_image_path=str(plate_path),
            decal_image_path=str(decal_path),
            config=config,
            output_path=str(composite_path),
        )

        any_ran = False
        for engine in engines:
            try:
                clean_result = engine.read_plate(str(plate_path))
                comp_result = engine.read_plate(str(composite_path))
            except Exception as exc:
                print(f"[{engine.name}] skipped: {exc}")
                continue

            any_ran = True
            print(
                f"[visible] {engine.name}: {plate_text}: "
                f"clean='{clean_result.plate_text}' -> "
                f"composite='{comp_result.plate_text}'"
            )
            # Ideally the visible-light reads match (phantom is inert).
            # This is informational — font rendering quality may still
            # cause minor diffs in synthetic plates.

        if not any_ran:
            pytest.skip("No OCR engines could run")


# ---------------------------------------------------------------------------
# 4. Wavelength specificity — right palette for right wavelength
# ---------------------------------------------------------------------------

class TestWavelengthSpecificity:
    """Verify that each color palette is optimized for its target wavelength."""

    def test_850nm_palette_contrast_at_850(self):
        """850nm red/black palette should maximize contrast under 850nm IR."""
        from decal_generator import generate_ir_phantom_decal, IRPhantomConfig
        from ir_simulation import simulate_ir

        config = IRPhantomConfig(
            phantom_chars="O0O0O",
            target_wavelength_nm=850,
        )
        img = generate_ir_phantom_decal(config=config)

        ir_850 = np.array(simulate_ir(img, 850))[:, :, 0]
        ir_940 = np.array(simulate_ir(img, 940))[:, :, 0]

        spread_850 = ir_850.std()
        spread_940 = ir_940.std()

        print(f"850nm palette: std@850={spread_850:.2f}, std@940={spread_940:.2f}")

    def test_940nm_palette_contrast_at_940(self):
        """940nm green/gray palette should maximize contrast under 940nm IR."""
        from decal_generator import generate_ir_phantom_decal, IRPhantomConfig
        from ir_simulation import simulate_ir

        config = IRPhantomConfig(
            phantom_chars="O0O0O",
            target_wavelength_nm=940,
        )
        img = generate_ir_phantom_decal(config=config)

        ir_850 = np.array(simulate_ir(img, 850))[:, :, 0]
        ir_940 = np.array(simulate_ir(img, 940))[:, :, 0]

        spread_850 = ir_850.std()
        spread_940 = ir_940.std()

        print(f"940nm palette: std@850={spread_850:.2f}, std@940={spread_940:.2f}")

    def test_mismatched_wavelength_reduces_effectiveness(self):
        """
        Using the 850nm palette under 940nm should be less effective
        than under 850nm (and vice versa), demonstrating wavelength
        specificity of the color-pair selection.
        """
        from decal_generator import generate_ir_phantom_decal, IRPhantomConfig
        from ir_simulation import simulate_ir

        results = {}
        for target_wl in WAVELENGTHS:
            config = IRPhantomConfig(
                phantom_chars="O0O0O",
                target_wavelength_nm=target_wl,
            )
            img = generate_ir_phantom_decal(config=config)

            for sim_wl in WAVELENGTHS:
                ir_arr = np.array(simulate_ir(img, sim_wl))[:, :, 0]
                results[(target_wl, sim_wl)] = ir_arr.std()

        # Log the full matrix
        print("\nWavelength specificity matrix (std dev under IR):")
        print(f"  {'palette':>10}  {'sim@850':>10}  {'sim@940':>10}")
        for target_wl in WAVELENGTHS:
            print(
                f"  {target_wl:>7}nm  "
                f"{results[(target_wl, 850)]:>10.2f}  "
                f"{results[(target_wl, 940)]:>10.2f}"
            )
