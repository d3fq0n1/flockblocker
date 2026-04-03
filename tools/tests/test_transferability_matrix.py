"""
Cross-engine transferability matrix tests.

Validates the transferability matrix computation that shows pairwise
engine-to-engine attack transfer rates — the core metric for estimating
whether adversarial decals exploit fundamental OCR weaknesses vs
engine-specific quirks (Vulnerability Catalog §2.3).
"""

import pytest

from evaluation import (
    DecalScore,
    SingleResult,
    TransferabilityCell,
    TransferabilityMatrix,
    compute_transferability_matrix,
    print_transferability_matrix,
)


def _make_result(engine, condition, plate, clean, decal, conf=0.9):
    """Helper to build a SingleResult."""
    return SingleResult(
        engine_name=engine,
        condition_name=condition,
        plate_text=plate,
        clean_read=clean,
        decal_read=decal,
        clean_confidence=conf,
        decal_confidence=conf,
    )


class TestTransferabilityCell:
    """Test individual matrix cell computation."""

    def test_transfer_rate_no_misreads(self):
        cell = TransferabilityCell("tesseract", "easyocr", co_misread_count=0, source_misread_count=0)
        assert cell.transfer_rate == 0.0

    def test_transfer_rate_full(self):
        cell = TransferabilityCell("tesseract", "easyocr", co_misread_count=10, source_misread_count=10)
        assert cell.transfer_rate == 1.0

    def test_transfer_rate_partial(self):
        cell = TransferabilityCell("tesseract", "easyocr", co_misread_count=7, source_misread_count=10)
        assert abs(cell.transfer_rate - 0.7) < 1e-9


class TestComputeTransferabilityMatrix:
    """Test matrix computation from DecalScore results."""

    def _build_scores(self):
        """Build test scores where engines have known transfer patterns."""
        score = DecalScore(decal_name="test_decal", strategy="confusion")

        # Case 1: All three engines misread (full transfer)
        score.results.append(_make_result("tesseract", "ideal", "ABC1234", "ABC1234", "A8C1234"))
        score.results.append(_make_result("easyocr", "ideal", "ABC1234", "ABC1234", "A8C1234"))
        score.results.append(_make_result("paddleocr", "ideal", "ABC1234", "ABC1234", "ABG1234"))

        # Case 2: Only tesseract and easyocr misread
        score.results.append(_make_result("tesseract", "mid_range", "ABC1234", "ABC1234", "A8C1234"))
        score.results.append(_make_result("easyocr", "mid_range", "ABC1234", "ABC1234", "ABG1234"))
        score.results.append(_make_result("paddleocr", "mid_range", "ABC1234", "ABC1234", "ABC1234"))

        # Case 3: Only tesseract misreads (no transfer)
        score.results.append(_make_result("tesseract", "far", "ABC1234", "ABC1234", "A8C1234"))
        score.results.append(_make_result("easyocr", "far", "ABC1234", "ABC1234", "ABC1234"))
        score.results.append(_make_result("paddleocr", "far", "ABC1234", "ABC1234", "ABC1234"))

        return [score]

    def test_engines_discovered(self):
        scores = self._build_scores()
        matrix = compute_transferability_matrix(scores)
        assert set(matrix.engines) == {"tesseract", "easyocr", "paddleocr"}

    def test_diagonal_is_one(self):
        """When an engine misreads, it always 'transfers' to itself."""
        scores = self._build_scores()
        matrix = compute_transferability_matrix(scores)
        for engine in matrix.engines:
            assert matrix.rate(engine, engine) == 1.0

    def test_tesseract_to_easyocr_transfer(self):
        """Tesseract misreads 3 times; easyocr also misreads in 2 of those."""
        scores = self._build_scores()
        matrix = compute_transferability_matrix(scores)
        # tesseract misreads in ideal, mid_range, far (3 times)
        # easyocr also misreads in ideal, mid_range (2 of 3)
        assert abs(matrix.rate("tesseract", "easyocr") - 2 / 3) < 1e-9

    def test_tesseract_to_paddleocr_transfer(self):
        """Tesseract misreads 3 times; paddleocr only in 1."""
        scores = self._build_scores()
        matrix = compute_transferability_matrix(scores)
        assert abs(matrix.rate("tesseract", "paddleocr") - 1 / 3) < 1e-9

    def test_easyocr_to_tesseract_transfer(self):
        """Easyocr misreads 2 times; tesseract also misreads in both."""
        scores = self._build_scores()
        matrix = compute_transferability_matrix(scores)
        assert matrix.rate("easyocr", "tesseract") == 1.0

    def test_paddleocr_to_others(self):
        """Paddleocr misreads only once (ideal); both others also misread there."""
        scores = self._build_scores()
        matrix = compute_transferability_matrix(scores)
        assert matrix.rate("paddleocr", "tesseract") == 1.0
        assert matrix.rate("paddleocr", "easyocr") == 1.0

    def test_mean_off_diagonal(self):
        scores = self._build_scores()
        matrix = compute_transferability_matrix(scores)
        # Off-diagonal pairs with data:
        # tes->easy: 2/3, tes->pad: 1/3, easy->tes: 1.0, easy->pad: 1/2,
        # pad->tes: 1.0, pad->easy: 1.0
        expected = (2 / 3 + 1 / 3 + 1.0 + 1 / 2 + 1.0 + 1.0) / 6
        assert abs(matrix.mean_off_diagonal - expected) < 1e-9

    def test_summary_serializable(self):
        """Summary dict should be JSON-serializable."""
        import json
        scores = self._build_scores()
        matrix = compute_transferability_matrix(scores)
        summary = matrix.summary()
        # Should not raise
        json.dumps(summary)
        assert "matrix" in summary
        assert "mean_off_diagonal_transfer" in summary
        assert "universal_misread_rate" in summary

    def test_empty_scores(self):
        matrix = compute_transferability_matrix([])
        assert matrix.engines == []
        assert matrix.mean_off_diagonal == 0.0


class TestPerStrategyMatrix:
    """Test that the matrix breaks down by attack strategy."""

    def _build_multi_strategy_scores(self):
        confusion_score = DecalScore(decal_name="confusion_v0", strategy="confusion")
        confusion_score.results.append(_make_result("tesseract", "ideal", "ABC1234", "ABC1234", "A8C1234"))
        confusion_score.results.append(_make_result("easyocr", "ideal", "ABC1234", "ABC1234", "A8C1234"))

        seg_score = DecalScore(decal_name="segmentation_v0", strategy="segmentation")
        seg_score.results.append(_make_result("tesseract", "ideal", "ABC1234", "ABC1234", "ABC12340"))
        seg_score.results.append(_make_result("easyocr", "ideal", "ABC1234", "ABC1234", "ABC1234"))

        return [confusion_score, seg_score]

    def test_strategy_matrices_populated(self):
        scores = self._build_multi_strategy_scores()
        matrix = compute_transferability_matrix(scores)
        assert "confusion" in matrix.strategy_matrices
        assert "segmentation" in matrix.strategy_matrices

    def test_confusion_transfers_fully(self):
        """Confusion attack fools both engines -> 100% transfer."""
        scores = self._build_multi_strategy_scores()
        matrix = compute_transferability_matrix(scores)
        assert matrix.strategy_rate("confusion", "tesseract", "easyocr") == 1.0

    def test_segmentation_does_not_transfer(self):
        """Segmentation fools tesseract but not easyocr -> 0% transfer."""
        scores = self._build_multi_strategy_scores()
        matrix = compute_transferability_matrix(scores)
        assert matrix.strategy_rate("segmentation", "tesseract", "easyocr") == 0.0

    def test_summary_includes_per_strategy(self):
        scores = self._build_multi_strategy_scores()
        matrix = compute_transferability_matrix(scores)
        summary = matrix.summary()
        assert "per_strategy" in summary
        assert "confusion" in summary["per_strategy"]
        assert "segmentation" in summary["per_strategy"]


class TestPrintTransferabilityMatrix:
    """Test the ASCII table formatter."""

    def test_output_contains_engines(self):
        score = DecalScore(decal_name="test", strategy="confusion")
        score.results.append(_make_result("tesseract", "ideal", "ABC1234", "ABC1234", "A8C1234"))
        score.results.append(_make_result("easyocr", "ideal", "ABC1234", "ABC1234", "A8C1234"))

        matrix = compute_transferability_matrix([score])
        output = print_transferability_matrix(matrix)

        assert "tesseract" in output
        assert "easyocr" in output
        assert "CROSS-ENGINE TRANSFERABILITY MATRIX" in output
        assert "Mean off-diagonal transfer" in output

    def test_output_contains_rates(self):
        score = DecalScore(decal_name="test", strategy="confusion")
        score.results.append(_make_result("tesseract", "ideal", "ABC1234", "ABC1234", "A8C1234"))
        score.results.append(_make_result("easyocr", "ideal", "ABC1234", "ABC1234", "A8C1234"))

        matrix = compute_transferability_matrix([score])
        output = print_transferability_matrix(matrix)

        # Diagonal should show 1.000
        assert "1.000" in output
