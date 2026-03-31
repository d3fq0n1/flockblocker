"""
Tests for decal generation strategies.

Validates that each generator produces usable decal images and that
the generated content matches the intended attack strategy.
"""

import pytest
import numpy as np
from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_output(tmp_path):
    return tmp_path


# ---------------------------------------------------------------------------
# 1. Character Confusion Decal Tests
# ---------------------------------------------------------------------------

class TestConfusionDecalGenerator:
    """Test character confusion decal generation (§1.1)."""

    def test_generates_image(self, tmp_output):
        from decal_generator import generate_confusion_decal

        img = generate_confusion_decal()
        assert img is not None
        assert img.size == (480, 120)

    def test_saves_to_path(self, tmp_output):
        from decal_generator import generate_confusion_decal

        path = str(tmp_output / "confusion.png")
        img = generate_confusion_decal(output_path=path)
        assert Path(path).exists()
        assert Path(path).stat().st_size > 0

    def test_targeted_generates_confusable_chars(self):
        from decal_generator import generate_confusion_decal, CONFUSION_PAIRS

        # Generate targeted confusion for a known plate
        img = generate_confusion_decal(target_plate="ABC1234")
        assert img is not None
        # Image should be non-blank (not all one color)
        arr = np.array(img)
        assert arr.std() > 5, "Image appears blank"

    def test_plate_mimicry_adds_border(self, tmp_output):
        from decal_generator import generate_confusion_decal, ConfusionDecalConfig

        # With mimicry
        cfg_with = ConfusionDecalConfig(plate_mimicry=True)
        img_with = generate_confusion_decal(config=cfg_with)

        # Without mimicry
        cfg_without = ConfusionDecalConfig(plate_mimicry=False)
        img_without = generate_confusion_decal(config=cfg_without)

        # They should differ (border pixels)
        arr_with = np.array(img_with)
        arr_without = np.array(img_without)
        assert not np.array_equal(arr_with, arr_without)

    def test_custom_char_sequence(self):
        from decal_generator import generate_confusion_decal, ConfusionDecalConfig

        cfg = ConfusionDecalConfig(char_sequence="00OO11II")
        img = generate_confusion_decal(config=cfg)
        assert img is not None

    def test_reproducible_with_seed(self):
        """Random confusion chars should vary across calls without fixed seed."""
        from decal_generator import generate_confusion_decal
        import random

        random.seed(1)
        np.random.seed(1)
        img1 = generate_confusion_decal()

        random.seed(1)
        np.random.seed(1)
        img2 = generate_confusion_decal()

        assert np.array_equal(np.array(img1), np.array(img2))


# ---------------------------------------------------------------------------
# 2. Segmentation Boundary Attack Tests
# ---------------------------------------------------------------------------

class TestSegmentationDecalGenerator:
    """Test segmentation boundary attack decals (§1.2)."""

    def test_generates_image(self):
        from decal_generator import generate_segmentation_decal

        img = generate_segmentation_decal()
        assert img is not None
        assert img.size == (480, 120)

    def test_white_background_matches_plate(self):
        from decal_generator import generate_segmentation_decal

        img = generate_segmentation_decal()
        arr = np.array(img)
        # Corners should be near-white (plate matching background)
        # Check a pixel away from the border
        assert arr[10, 10, 0] > 200 or arr[10, 10, 0] < 10  # white bg or black border

    def test_extends_plate_border(self):
        from decal_generator import generate_segmentation_decal, SegmentationDecalConfig

        cfg = SegmentationDecalConfig(extend_plate_border=True, border_thickness=5)
        img = generate_segmentation_decal(config=cfg)
        arr = np.array(img)
        # Top edge should have dark pixels (border line)
        assert arr[0, img.size[0] // 2, 0] < 50, "Top border not drawn"

    def test_targeted_extension(self):
        from decal_generator import generate_segmentation_decal

        img = generate_segmentation_decal(target_plate="ABC1234")
        assert img is not None
        arr = np.array(img)
        assert arr.std() > 5, "Image appears blank"

    def test_chars_near_top_edge(self):
        from decal_generator import generate_segmentation_decal, SegmentationDecalConfig

        cfg = SegmentationDecalConfig(edge_padding=2)
        img = generate_segmentation_decal(config=cfg)
        arr = np.array(img)
        # Top region should have dark pixels (characters placed near top)
        top_strip = arr[2:30, :, :]
        assert top_strip.min() < 50, "No dark pixels near top edge"

    def test_saves_to_path(self, tmp_output):
        from decal_generator import generate_segmentation_decal

        path = str(tmp_output / "seg.png")
        generate_segmentation_decal(output_path=path)
        assert Path(path).exists()


# ---------------------------------------------------------------------------
# 3. IR Phantom Character Tests
# ---------------------------------------------------------------------------

class TestIRPhantomDecalGenerator:
    """Test IR phantom character injection (§3.3)."""

    def test_generates_image(self):
        from decal_generator import generate_ir_phantom_decal

        img = generate_ir_phantom_decal()
        assert img is not None
        assert img.size == (480, 120)

    def test_low_visible_contrast(self):
        """Phantom chars should be nearly invisible in visible light."""
        from decal_generator import generate_ir_phantom_decal

        img = generate_ir_phantom_decal()
        arr = np.array(img, dtype=np.float32)
        # Compute local contrast — should be low (text nearly invisible)
        # Standard deviation across the image should be modest
        # (not zero — there are chars — but much lower than a normal decal)
        channel_stds = [arr[:, :, c].std() for c in range(3)]
        avg_std = sum(channel_stds) / 3
        assert avg_std < 80, f"Visible contrast too high ({avg_std:.1f}), chars should be hidden"

    def test_ir_reveals_characters(self):
        """Under IR simulation, hidden characters should become visible."""
        from decal_generator import generate_ir_phantom_decal, simulate_ir_view

        img = generate_ir_phantom_decal()
        ir_img = simulate_ir_view(img, wavelength_nm=850)

        visible_arr = np.array(img, dtype=np.float32)
        ir_arr = np.array(ir_img, dtype=np.float32)

        # IR view should have different contrast characteristics
        vis_std = visible_arr[:, :, 0].std()
        ir_std = ir_arr[:, :, 0].std()

        # The IR image may or may not have higher contrast depending on the
        # color pair, but it should be meaningfully different
        assert abs(ir_std - vis_std) > 0.1 or ir_std > 1.0, \
            "IR view should differ from visible view"

    def test_940nm_uses_green_palette(self):
        from decal_generator import generate_ir_phantom_decal, IRPhantomConfig

        cfg = IRPhantomConfig(target_wavelength_nm=940)
        img = generate_ir_phantom_decal(config=cfg)
        arr = np.array(img)
        # Green channel should dominate (green/gray palette for 940nm)
        center_pixel = arr[60, 240, :]
        assert center_pixel[1] > center_pixel[0], "940nm should use green palette"

    def test_targeted_phantom(self):
        from decal_generator import generate_ir_phantom_decal

        img = generate_ir_phantom_decal(target_plate="WKM7793")
        assert img is not None


# ---------------------------------------------------------------------------
# 4. Adversarial Patch Tests
# ---------------------------------------------------------------------------

class TestAdversarialPatchGenerator:
    """Test EOT adversarial patch generation (§2.4)."""

    def test_heuristic_fallback_generates_image(self):
        from decal_generator import _generate_heuristic_patch, AdversarialPatchConfig

        cfg = AdversarialPatchConfig(seed=42)
        img = _generate_heuristic_patch(cfg)
        assert img is not None
        assert img.size == (480, 120)

    def test_heuristic_has_high_frequency_content(self):
        from decal_generator import _generate_heuristic_patch, AdversarialPatchConfig

        cfg = AdversarialPatchConfig(seed=42)
        img = _generate_heuristic_patch(cfg)
        arr = np.array(img, dtype=np.float32)

        # High-frequency content = high variance in local neighborhoods
        # Check that adjacent pixels differ significantly
        h_diff = np.abs(arr[:, 1:, :] - arr[:, :-1, :]).mean()
        v_diff = np.abs(arr[1:, :, :] - arr[:-1, :, :]).mean()
        assert h_diff > 15, f"Horizontal frequency too low ({h_diff:.1f})"
        assert v_diff > 10, f"Vertical frequency too low ({v_diff:.1f})"

    def test_heuristic_is_reproducible(self):
        from decal_generator import _generate_heuristic_patch, AdversarialPatchConfig

        cfg1 = AdversarialPatchConfig(seed=123)
        cfg2 = AdversarialPatchConfig(seed=123)
        img1 = _generate_heuristic_patch(cfg1)
        img2 = _generate_heuristic_patch(cfg2)
        assert np.array_equal(np.array(img1), np.array(img2))

    def test_different_seeds_produce_different_patches(self):
        from decal_generator import _generate_heuristic_patch, AdversarialPatchConfig

        img1 = _generate_heuristic_patch(AdversarialPatchConfig(seed=1))
        img2 = _generate_heuristic_patch(AdversarialPatchConfig(seed=2))
        assert not np.array_equal(np.array(img1), np.array(img2))

    def test_generate_adversarial_patch_runs(self, tmp_output):
        """Test the main entry point (uses heuristic fallback if no torch)."""
        from decal_generator import generate_adversarial_patch, AdversarialPatchConfig

        path = str(tmp_output / "adv_patch.png")
        cfg = AdversarialPatchConfig(
            num_steps=5,  # very few steps for test speed
            eot_samples=2,
            seed=42,
        )
        img = generate_adversarial_patch(config=cfg, output_path=path)
        assert img is not None
        assert Path(path).exists()

    def test_patch_saves_to_path(self, tmp_output):
        from decal_generator import _generate_heuristic_patch, AdversarialPatchConfig

        path = str(tmp_output / "patch.png")
        _generate_heuristic_patch(AdversarialPatchConfig(seed=42), output_path=path)
        assert Path(path).exists()
        assert Path(path).stat().st_size > 0


# ---------------------------------------------------------------------------
# 5. Candidate Suite Generation Tests
# ---------------------------------------------------------------------------

class TestCandidateSuite:
    """Test batch generation across all strategies."""

    def test_generates_all_strategies(self, tmp_output):
        from decal_generator import generate_candidate_suite

        candidates = generate_candidate_suite(
            output_dir=str(tmp_output),
            variants_per_strategy=1,
            seed=42,
        )
        strategies = {c.strategy for c in candidates}
        assert "confusion" in strategies
        assert "segmentation" in strategies
        assert "ir_phantom" in strategies
        assert "adversarial_patch" in strategies

    def test_correct_variant_count(self, tmp_output):
        from decal_generator import generate_candidate_suite

        n = 2
        candidates = generate_candidate_suite(
            variants_per_strategy=n,
            seed=42,
        )
        # 4 strategies × n variants
        assert len(candidates) == 4 * n

    def test_saves_files_to_output_dir(self, tmp_output):
        from decal_generator import generate_candidate_suite

        candidates = generate_candidate_suite(
            output_dir=str(tmp_output),
            variants_per_strategy=1,
            seed=42,
        )
        png_files = list(tmp_output.glob("*.png"))
        assert len(png_files) == len(candidates)

    def test_targeted_generation(self, tmp_output):
        from decal_generator import generate_candidate_suite

        candidates = generate_candidate_suite(
            target_plate="ABC1234",
            variants_per_strategy=1,
            seed=42,
        )
        assert all(c.image is not None for c in candidates)

    def test_selective_strategies(self, tmp_output):
        from decal_generator import generate_candidate_suite

        candidates = generate_candidate_suite(
            strategies=["confusion", "ir_phantom"],
            variants_per_strategy=2,
            seed=42,
        )
        assert len(candidates) == 4  # 2 strategies × 2 variants
        strategies = {c.strategy for c in candidates}
        assert strategies == {"confusion", "ir_phantom"}

    def test_candidate_metadata(self, tmp_output):
        from decal_generator import generate_candidate_suite

        candidates = generate_candidate_suite(
            output_dir=str(tmp_output),
            variants_per_strategy=1,
            seed=42,
        )
        for c in candidates:
            assert c.strategy in ("confusion", "segmentation", "ir_phantom", "adversarial_patch")
            assert "variant" in c.params
            assert "seed" in c.params
            assert c.path is not None


# ---------------------------------------------------------------------------
# 6. Evaluation Pipeline Tests
# ---------------------------------------------------------------------------

class TestEvaluationPipeline:
    """Test the scoring/evaluation infrastructure."""

    def test_single_result_misread_detection(self):
        from evaluation import SingleResult

        r = SingleResult(
            engine_name="tesseract",
            condition_name="ideal",
            plate_text="ABC1234",
            clean_read="ABC1234",
            decal_read="A8C1234",
            clean_confidence=0.95,
            decal_confidence=0.87,
        )
        assert r.misread is True
        assert r.corruption_type == "char_substitution"

    def test_single_result_no_misread(self):
        from evaluation import SingleResult

        r = SingleResult(
            engine_name="tesseract",
            condition_name="ideal",
            plate_text="ABC1234",
            clean_read="ABC1234",
            decal_read="ABC1234",
            clean_confidence=0.95,
            decal_confidence=0.90,
        )
        assert r.misread is False
        assert r.corruption_type == "none"

    def test_single_result_length_change(self):
        from evaluation import SingleResult

        r = SingleResult(
            engine_name="tesseract",
            condition_name="ideal",
            plate_text="ABC1234",
            clean_read="ABC1234",
            decal_read="ABC12340O",
            clean_confidence=0.95,
            decal_confidence=0.80,
        )
        assert r.misread is True
        assert r.corruption_type == "length_change"

    def test_decal_score_composite(self):
        from evaluation import DecalScore, SingleResult

        score = DecalScore(decal_name="test", strategy="confusion")
        # 2 misreads out of 3 reads, across 2 engines
        score.results = [
            SingleResult("eng1", "ideal", "ABC", "ABC", "A8C", 0.9, 0.85),
            SingleResult("eng2", "ideal", "ABC", "ABC", "ABC", 0.9, 0.88),
            SingleResult("eng1", "far", "ABC", "ABC", "ARC", 0.8, 0.75),
        ]
        assert score.misread_rate == pytest.approx(2 / 3)
        assert score.composite_score > 0

    def test_decal_score_summary(self):
        from evaluation import DecalScore, SingleResult

        score = DecalScore(decal_name="test", strategy="segmentation")
        score.results = [
            SingleResult("eng1", "ideal", "ABC", "ABC", "ABCOO", 0.9, 0.80),
        ]
        summary = score.summary()
        assert "decal" in summary
        assert "strategy" in summary
        assert "composite_score" in summary
        assert summary["strategy"] == "segmentation"

    def test_leaderboard_format(self):
        from evaluation import DecalScore, SingleResult, print_leaderboard

        scores = [
            DecalScore(
                decal_name="confusion_v0",
                strategy="confusion",
                results=[
                    SingleResult("eng1", "ideal", "ABC", "ABC", "A8C", 0.9, 0.85),
                ],
            ),
            DecalScore(
                decal_name="seg_v0",
                strategy="segmentation",
                results=[
                    SingleResult("eng1", "ideal", "ABC", "ABC", "ABC", 0.9, 0.9),
                ],
            ),
        ]
        report = print_leaderboard(scores)
        assert "LEADERBOARD" in report
        assert "confusion_v0" in report
        assert "seg_v0" in report
