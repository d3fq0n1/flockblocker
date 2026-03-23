"""
Baseline OCR accuracy tests.

Establishes how well each OCR engine reads clean plates — the control group.
Without this baseline, we can't measure adversarial effectiveness.
"""

import pytest
from pathlib import Path

# Known test plates and their expected reads
KNOWN_PLATES = [
    ("ABC1234", "WI"),
    ("XYZ9876", "WI"),
    ("HBR4051", "WI"),
    # Plates with commonly confused characters
    ("BOO8008", "WI"),   # B/8, O/0 confusion
    ("ILL1100", "WI"),   # I/1, L/1 confusion
    ("SGS5255", "WI"),   # S/5 confusion
]


@pytest.fixture
def synthetic_plates(tmp_path):
    """Generate synthetic plate images for baseline testing."""
    from plate_compositor import generate_test_plate

    plates = {}
    for text, state in KNOWN_PLATES:
        path = tmp_path / f"plate_{text}.png"
        generate_test_plate(plate_text=text, state=state, output_path=str(path))
        plates[text] = path
    return plates


class TestBaselineAccuracy:
    """Test OCR engines against clean synthetic plates."""

    def _get_engine(self, engine_name):
        from ocr_engines import get_engine
        try:
            return get_engine(engine_name)
        except Exception:
            pytest.skip(f"{engine_name} not available")

    @pytest.mark.parametrize("plate_text,state", KNOWN_PLATES)
    def test_tesseract_reads_clean_plate(self, synthetic_plates, plate_text, state):
        engine = self._get_engine("tesseract")
        result = engine.read_plate(str(synthetic_plates[plate_text]))
        assert result.plate_text == plate_text, (
            f"Tesseract read '{result.plate_text}' (conf: {result.confidence:.2f}), "
            f"expected '{plate_text}'"
        )

    @pytest.mark.parametrize("plate_text,state", KNOWN_PLATES)
    def test_easyocr_reads_clean_plate(self, synthetic_plates, plate_text, state):
        engine = self._get_engine("easyocr")
        result = engine.read_plate(str(synthetic_plates[plate_text]))
        assert result.plate_text == plate_text, (
            f"EasyOCR read '{result.plate_text}' (conf: {result.confidence:.2f}), "
            f"expected '{plate_text}'"
        )

    @pytest.mark.parametrize("plate_text,state", KNOWN_PLATES)
    def test_paddleocr_reads_clean_plate(self, synthetic_plates, plate_text, state):
        engine = self._get_engine("paddleocr")
        result = engine.read_plate(str(synthetic_plates[plate_text]))
        assert result.plate_text == plate_text, (
            f"PaddleOCR read '{result.plate_text}' (conf: {result.confidence:.2f}), "
            f"expected '{plate_text}'"
        )


class TestConfusionCharacters:
    """
    Test which character pairs cause OCR confusion even on clean plates.

    This maps directly to Vulnerability Catalog §1.1 (Character Confusion Pairs).
    Baseline confusion rates on clean plates tell us which characters are already
    fragile — and therefore easiest to push into misreads with a nearby decal.
    """

    CONFUSION_PAIRS = [
        ("0", "O"), ("0", "D"), ("0", "Q"),
        ("1", "I"), ("1", "L"),
        ("8", "B"),
        ("5", "S"),
        ("2", "Z"),
        ("6", "G"),
    ]

    @pytest.fixture
    def confusion_plates(self, tmp_path):
        """Generate plates that contain easily confused characters."""
        from plate_compositor import generate_test_plate

        plates = {}
        for c1, c2 in self.CONFUSION_PAIRS:
            for char in (c1, c2):
                text = f"A{char}{char}1{char}{char}A"
                if text not in plates:
                    path = tmp_path / f"confusion_{text}.png"
                    generate_test_plate(plate_text=text, output_path=str(path))
                    plates[text] = path
        return plates

    def test_confusion_pair_baseline(self, confusion_plates):
        """Log confusion rates for each character pair — informational, not pass/fail."""
        from ocr_engines import get_all_engines

        engines = get_all_engines()
        if not engines:
            pytest.skip("No OCR engines available")

        results = []
        for c1, c2 in self.CONFUSION_PAIRS:
            for char in (c1, c2):
                text = f"A{char}{char}1{char}{char}A"
                path = confusion_plates[text]
                for engine in engines:
                    result = engine.read_plate(str(path))
                    confused = result.plate_text != text
                    results.append({
                        "expected": text,
                        "engine": engine.name,
                        "read": result.plate_text,
                        "confidence": result.confidence,
                        "confused": confused,
                    })

        # Report confusion rates
        confused_count = sum(1 for r in results if r["confused"])
        total = len(results)
        print(f"\nConfusion rate: {confused_count}/{total} ({100*confused_count/total:.1f}%)")
        for r in results:
            if r["confused"]:
                print(f"  {r['engine']}: expected '{r['expected']}' got '{r['read']}' "
                      f"(conf: {r['confidence']:.2f})")
