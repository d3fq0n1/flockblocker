"""
Decal effectiveness tests.

Measures how a decal placed near a plate affects OCR reads.
This is the core test: does the sticker cause misreads?
"""

import pytest
from pathlib import Path

# Test matrix: plate text × decal position × simulated conditions
PLATE_TEXTS = ["ABC1234", "HBR4051", "WKM7793"]
DECAL_POSITIONS = ["below", "above", "left", "right"]
DISTANCES_FT = [15.0, 25.0, 40.0]


class TestDecalEffect:
    """Test how decals near plates affect OCR reads."""

    @pytest.fixture
    def plate_images(self, tmp_path):
        """Generate test plate images."""
        from plate_compositor import generate_test_plate

        plates = {}
        for text in PLATE_TEXTS:
            path = tmp_path / f"plate_{text}.png"
            generate_test_plate(plate_text=text, output_path=str(path))
            plates[text] = path
        return plates

    def _run_ocr_comparison(self, plate_path, composite_path, engine_name="tesseract"):
        """Compare OCR results between clean plate and plate+decal composite."""
        from ocr_engines import get_engine

        try:
            engine = get_engine(engine_name)
        except Exception:
            pytest.skip(f"{engine_name} not available")

        clean_result = engine.read_plate(str(plate_path))
        composite_result = engine.read_plate(str(composite_path))

        return {
            "clean_text": clean_result.plate_text,
            "clean_confidence": clean_result.confidence,
            "composite_text": composite_result.plate_text,
            "composite_confidence": composite_result.confidence,
            "text_changed": clean_result.plate_text != composite_result.plate_text,
            "confidence_delta": composite_result.confidence - clean_result.confidence,
        }

    @pytest.mark.parametrize("plate_text", PLATE_TEXTS)
    @pytest.mark.parametrize("position", DECAL_POSITIONS)
    def test_decal_causes_misread(self, plate_images, plate_text, position, tmp_path, decals_dir):
        """Test if a decal in a given position causes a misread."""
        from plate_compositor import create_composite, CompositeConfig

        # Skip if no decal fixtures exist yet
        if not decals_dir.exists() or not list(decals_dir.glob("*.png")):
            pytest.skip("No decal fixtures available — generate decals first")

        decal_path = next(decals_dir.glob("*.png"))
        composite_path = tmp_path / f"composite_{plate_text}_{position}.png"

        config = CompositeConfig(decal_position=position)
        create_composite(
            plate_image_path=str(plate_images[plate_text]),
            decal_image_path=str(decal_path),
            config=config,
            output_path=str(composite_path),
        )

        result = self._run_ocr_comparison(plate_images[plate_text], composite_path)

        # Log the result regardless of pass/fail
        print(f"\n[{position}] {plate_text}: "
              f"clean='{result['clean_text']}' ({result['clean_confidence']:.2f}) → "
              f"composite='{result['composite_text']}' ({result['composite_confidence']:.2f})")

        if result["text_changed"]:
            print(f"  ✓ MISREAD INDUCED: '{result['clean_text']}' → '{result['composite_text']}'")

    @pytest.mark.parametrize("plate_text", PLATE_TEXTS)
    @pytest.mark.parametrize("distance_ft", DISTANCES_FT)
    def test_decal_effect_at_distance(self, plate_images, plate_text, distance_ft, tmp_path, decals_dir):
        """Test decal effectiveness at different simulated distances."""
        from plate_compositor import create_composite, CompositeConfig

        if not decals_dir.exists() or not list(decals_dir.glob("*.png")):
            pytest.skip("No decal fixtures available")

        decal_path = next(decals_dir.glob("*.png"))
        composite_path = tmp_path / f"composite_{plate_text}_{distance_ft}ft.png"

        config = CompositeConfig(
            decal_position="below",
            distance_ft=distance_ft,
        )
        create_composite(
            plate_image_path=str(plate_images[plate_text]),
            decal_image_path=str(decal_path),
            config=config,
            output_path=str(composite_path),
        )

        result = self._run_ocr_comparison(plate_images[plate_text], composite_path)

        print(f"\n[{distance_ft}ft] {plate_text}: "
              f"clean='{result['clean_text']}' → composite='{result['composite_text']}' "
              f"(Δconf: {result['confidence_delta']:+.2f})")


class TestIRSimulation:
    """Test decal effectiveness under simulated IR capture conditions."""

    @pytest.fixture
    def plate_images(self, tmp_path):
        from plate_compositor import generate_test_plate

        plates = {}
        for text in PLATE_TEXTS:
            path = tmp_path / f"plate_{text}.png"
            generate_test_plate(plate_text=text, output_path=str(path))
            plates[text] = path
        return plates

    @pytest.mark.parametrize("plate_text", PLATE_TEXTS)
    @pytest.mark.parametrize("wavelength", [850, 940])
    def test_ir_decal_effect(self, plate_images, plate_text, wavelength, tmp_path, decals_dir):
        """Test if decal effectiveness changes under IR simulation."""
        from plate_compositor import create_composite, CompositeConfig

        if not decals_dir.exists() or not list(decals_dir.glob("*.png")):
            pytest.skip("No decal fixtures available")

        decal_path = next(decals_dir.glob("*.png"))

        # Create both visible-light and IR composites
        visible_path = tmp_path / f"visible_{plate_text}.png"
        ir_path = tmp_path / f"ir_{plate_text}_{wavelength}nm.png"

        config_visible = CompositeConfig(decal_position="below", simulate_ir=False)
        config_ir = CompositeConfig(
            decal_position="below", simulate_ir=True, ir_wavelength_nm=wavelength
        )

        create_composite(
            str(plate_images[plate_text]), str(decal_path),
            config=config_visible, output_path=str(visible_path),
        )
        create_composite(
            str(plate_images[plate_text]), str(decal_path),
            config=config_ir, output_path=str(ir_path),
        )

        from ocr_engines import get_all_engines

        engines = get_all_engines()
        if not engines:
            pytest.skip("No OCR engines available")

        for engine in engines:
            vis_result = engine.read_plate(str(visible_path))
            ir_result = engine.read_plate(str(ir_path))

            print(f"\n[{engine.name}] {plate_text} @ {wavelength}nm: "
                  f"visible='{vis_result.plate_text}' ({vis_result.confidence:.2f}) "
                  f"→ IR='{ir_result.plate_text}' ({ir_result.confidence:.2f})")


class TestEnsembleTransferability:
    """
    Test if a decal that fools one OCR engine also fools others.

    Maps to Vulnerability Catalog §2.3 (Transferability Across OCR Architectures).
    High transferability = higher chance of fooling Flock's proprietary OCR.
    """

    @pytest.fixture
    def plate_images(self, tmp_path):
        from plate_compositor import generate_test_plate

        plates = {}
        for text in PLATE_TEXTS:
            path = tmp_path / f"plate_{text}.png"
            generate_test_plate(plate_text=text, output_path=str(path))
            plates[text] = path
        return plates

    @pytest.mark.parametrize("plate_text", PLATE_TEXTS)
    def test_cross_engine_misread_rate(self, plate_images, plate_text, tmp_path, decals_dir):
        """Measure misread consistency across all available OCR engines."""
        from plate_compositor import create_composite, CompositeConfig
        from ocr_engines import get_all_engines

        if not decals_dir.exists() or not list(decals_dir.glob("*.png")):
            pytest.skip("No decal fixtures available")

        engines = get_all_engines()
        if len(engines) < 2:
            pytest.skip("Need at least 2 OCR engines for transferability test")

        decal_path = next(decals_dir.glob("*.png"))
        composite_path = tmp_path / f"composite_{plate_text}.png"

        config = CompositeConfig(decal_position="below")
        create_composite(
            str(plate_images[plate_text]), str(decal_path),
            config=config, output_path=str(composite_path),
        )

        results = {}
        for engine in engines:
            clean = engine.read_plate(str(plate_images[plate_text]))
            composite = engine.read_plate(str(composite_path))
            results[engine.name] = {
                "clean": clean.plate_text,
                "composite": composite.plate_text,
                "misread": clean.plate_text != composite.plate_text,
            }

        misread_count = sum(1 for r in results.values() if r["misread"])
        total = len(results)
        transferability = misread_count / total

        print(f"\n{plate_text} transferability: {misread_count}/{total} engines "
              f"({100*transferability:.0f}%)")
        for engine_name, r in results.items():
            status = "MISREAD" if r["misread"] else "correct"
            print(f"  {engine_name}: '{r['clean']}' → '{r['composite']}' [{status}]")
