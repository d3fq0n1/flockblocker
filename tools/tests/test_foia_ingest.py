"""Tests for FOIA image ingestion pipeline."""

import json
import tempfile
from pathlib import Path

import pytest
import numpy as np

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from foia_ingest import (
    FOIAImage,
    FOIACatalog,
    NormalizeConfig,
    EngineAccuracy,
    BenchmarkResult,
    ingest_directory,
    normalize_image,
    normalize_catalog,
    generate_placeholders,
    benchmark_catalog,
    print_benchmark_report,
    _compute_file_hash,
    _char_match_ratio,
)


pytestmark = pytest.mark.skipif(not HAS_PIL, reason="Pillow required")


# ═══════════════════════════════════════════════════════════════════════════
# Data model
# ═══════════════════════════════════════════════════════════════════════════

class TestFOIAImage:
    def test_to_dict_roundtrip(self):
        img = FOIAImage(
            image_id="test-123",
            source_file="capture.jpg",
            ground_truth="ABC1234",
            state="WI",
            is_placeholder=True,
        )
        d = img.to_dict()
        restored = FOIAImage.from_dict(d)
        assert restored.image_id == "test-123"
        assert restored.ground_truth == "ABC1234"
        assert restored.is_placeholder is True

    def test_from_dict_ignores_extra_keys(self):
        d = {"image_id": "x", "source_file": "y", "extra_field": "ignored"}
        img = FOIAImage.from_dict(d)
        assert img.image_id == "x"


class TestFOIACatalog:
    def test_properties(self):
        catalog = FOIACatalog()
        catalog.images = [
            FOIAImage(image_id="1", source_file="a.png", ground_truth="ABC", is_placeholder=True),
            FOIAImage(image_id="2", source_file="b.png", ground_truth="", is_placeholder=False),
            FOIAImage(image_id="3", source_file="c.png", ground_truth="XYZ", is_placeholder=True),
        ]
        assert catalog.total_images == 3
        assert catalog.labeled_count == 2
        assert catalog.placeholder_count == 2

    def test_save_and_load(self):
        catalog = FOIACatalog(source_description="test", agency="test agency")
        catalog.images.append(FOIAImage(
            image_id="test-id",
            source_file="test.png",
            ground_truth="WKM7793",
        ))

        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "catalog.json")
            catalog.save(path)

            loaded = FOIACatalog.load(path)
            assert loaded.source_description == "test"
            assert loaded.agency == "test agency"
            assert len(loaded.images) == 1
            assert loaded.images[0].ground_truth == "WKM7793"


# ═══════════════════════════════════════════════════════════════════════════
# Ingestion
# ═══════════════════════════════════════════════════════════════════════════

class TestIngestion:
    def test_ingest_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Create some test images
            for name in ["capture_001.png", "capture_002.jpg", "notes.txt"]:
                path = Path(tmp) / name
                if name.endswith((".png", ".jpg")):
                    Image.new("RGB", (100, 100), (128, 128, 128)).save(str(path))
                else:
                    path.write_text("not an image")

            catalog = ingest_directory(tmp, source_description="Test FOIA")
            # Should find 2 images, not the .txt file
            assert catalog.total_images == 2
            assert catalog.source_description == "Test FOIA"

            # Each entry should have a hash
            for entry in catalog.images:
                assert len(entry.source_hash) == 16

    def test_ingest_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            catalog = ingest_directory(tmp)
            assert catalog.total_images == 0

    def test_ingest_nonexistent_raises(self):
        with pytest.raises(FileNotFoundError):
            ingest_directory("/nonexistent/path")


# ═══════════════════════════════════════════════════════════════════════════
# Normalization
# ═══════════════════════════════════════════════════════════════════════════

class TestNormalization:
    def test_normalize_image_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Create a test image
            src = Path(tmp) / "raw.png"
            Image.new("RGB", (800, 600), (100, 100, 100)).save(str(src))

            dst = Path(tmp) / "normalized.png"
            meta = normalize_image(str(src), str(dst))

            assert dst.exists()
            img = Image.open(str(dst))
            assert img.size == (640, 480)
            assert "crop_box" in meta

    def test_normalize_with_crop_region(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "raw.png"
            Image.new("RGB", (800, 600), (100, 100, 100)).save(str(src))

            dst = Path(tmp) / "cropped.png"
            config = NormalizeConfig(
                target_width=320,
                target_height=240,
                plate_region=(100, 100, 500, 400),
            )
            meta = normalize_image(str(src), str(dst), config)
            assert meta["crop_box"] == (100, 100, 500, 400)

    def test_normalize_grayscale(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "raw.png"
            Image.new("RGB", (200, 200), (255, 0, 0)).save(str(src))

            dst = Path(tmp) / "gray.png"
            config = NormalizeConfig(grayscale=True)
            normalize_image(str(src), str(dst), config)

            img = Image.open(str(dst))
            arr = np.array(img)
            # All channels should be equal (grayscale)
            assert np.array_equal(arr[:, :, 0], arr[:, :, 1])
            assert np.array_equal(arr[:, :, 1], arr[:, :, 2])


# ═══════════════════════════════════════════════════════════════════════════
# Placeholder generation
# ═══════════════════════════════════════════════════════════════════════════

class TestPlaceholders:
    def test_generate_placeholders(self):
        with tempfile.TemporaryDirectory() as tmp:
            catalog = generate_placeholders(tmp, count=5, seed=42)
            assert catalog.total_images == 5
            assert catalog.labeled_count == 5  # all have ground_truth
            assert catalog.placeholder_count == 5

            # All images should exist
            for entry in catalog.images:
                path = Path(tmp) / entry.source_file
                assert path.exists(), f"Missing: {path}"

            # Catalog JSON should be written
            assert (Path(tmp) / "catalog.json").exists()

    def test_placeholders_have_ground_truth(self):
        with tempfile.TemporaryDirectory() as tmp:
            catalog = generate_placeholders(tmp, count=3, seed=42)
            for entry in catalog.images:
                assert entry.ground_truth, "Placeholder missing ground truth"
                assert entry.state, "Placeholder missing state"
                assert entry.is_placeholder is True

    def test_placeholders_reproducible(self):
        with tempfile.TemporaryDirectory() as tmp1, \
             tempfile.TemporaryDirectory() as tmp2:
            c1 = generate_placeholders(tmp1, count=3, seed=42)
            c2 = generate_placeholders(tmp2, count=3, seed=42)
            for e1, e2 in zip(c1.images, c2.images):
                assert e1.ground_truth == e2.ground_truth
                assert e1.state == e2.state


# ═══════════════════════════════════════════════════════════════════════════
# Benchmark & accuracy
# ═══════════════════════════════════════════════════════════════════════════

class TestBenchmark:
    def test_char_match_ratio(self):
        assert _char_match_ratio("ABC1234", "ABC1234") == 1.0
        assert _char_match_ratio("ABC1234", "ABC1235") == 6 / 7
        assert _char_match_ratio("ABC", "") == 0.0
        assert _char_match_ratio("", "ABC") == 0.0

    def test_engine_accuracy_properties(self):
        acc = EngineAccuracy(engine_name="test")
        acc.total_reads = 10
        acc.exact_matches = 7
        acc.partial_matches = 2
        acc.total_confidence = 8.5
        assert acc.exact_accuracy == 0.7
        assert acc.partial_accuracy == 0.9
        assert abs(acc.avg_confidence - 0.85) < 0.001

    def test_engine_accuracy_empty(self):
        acc = EngineAccuracy(engine_name="test")
        assert acc.exact_accuracy == 0.0
        assert acc.avg_confidence == 0.0

    def test_benchmark_result_to_dict(self):
        result = BenchmarkResult(total_images=10, labeled_images=8)
        result.engine_results["test"] = EngineAccuracy(
            engine_name="test",
            total_reads=8,
            exact_matches=6,
        )
        d = result.to_dict()
        assert d["total_images"] == 10
        assert "test" in d["engines"]

    def test_print_benchmark_report(self):
        result = BenchmarkResult(total_images=5, labeled_images=5)
        result.engine_results["mock"] = EngineAccuracy(
            engine_name="mock",
            total_reads=5,
            exact_matches=3,
            total_confidence=4.0,
        )
        report = print_benchmark_report(result)
        assert "FOIA IMAGE BENCHMARK REPORT" in report
        assert "mock" in report


# ═══════════════════════════════════════════════════════════════════════════
# Utility functions
# ═══════════════════════════════════════════════════════════════════════════

class TestUtils:
    def test_file_hash_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.bin"
            path.write_bytes(b"hello world")
            h1 = _compute_file_hash(path)
            h2 = _compute_file_hash(path)
            assert h1 == h2
            assert len(h1) == 16

    def test_file_hash_differs(self):
        with tempfile.TemporaryDirectory() as tmp:
            p1 = Path(tmp) / "a.bin"
            p2 = Path(tmp) / "b.bin"
            p1.write_bytes(b"hello")
            p2.write_bytes(b"world")
            assert _compute_file_hash(p1) != _compute_file_hash(p2)
