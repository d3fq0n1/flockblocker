"""
Unified interface to multiple OCR engines for ensemble testing.

Tests adversarial decal effectiveness across multiple OCR backends to
estimate transferability to Flock's proprietary pipeline.
"""

from dataclasses import dataclass


@dataclass
class OCRResult:
    """Result from a single OCR engine read attempt."""
    engine: str
    text: str
    confidence: float
    raw_output: dict

    @property
    def plate_text(self) -> str:
        """Normalized plate text (uppercase, no spaces/dashes)."""
        return self.text.upper().replace(" ", "").replace("-", "")


class OCREngine:
    """Base class for OCR engine wrappers."""

    name: str = "base"

    def read_plate(self, image_path: str) -> OCRResult:
        raise NotImplementedError

    def read_plate_region(self, image_path: str, bbox: tuple) -> OCRResult:
        """Read plate from a specific bounding box region."""
        raise NotImplementedError


class TesseractEngine(OCREngine):
    """Tesseract OCR — most widely deployed open-source OCR."""

    name = "tesseract"

    def __init__(self, psm_mode: int = 7):
        """
        Args:
            psm_mode: Page segmentation mode. 7 = single line of text
                      (appropriate for plate reads).
        """
        self.psm_mode = psm_mode

    def read_plate(self, image_path: str) -> OCRResult:
        import pytesseract
        from PIL import Image

        img = Image.open(image_path)
        data = pytesseract.image_to_data(
            img,
            config=f"--psm {self.psm_mode} -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
            output_type=pytesseract.Output.DICT,
        )

        # Extract highest-confidence text
        texts = []
        confidences = []
        for i, conf in enumerate(data["conf"]):
            if int(conf) > 0:
                texts.append(data["text"][i])
                confidences.append(int(conf))

        text = "".join(texts)
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

        return OCRResult(
            engine=self.name,
            text=text,
            confidence=avg_conf / 100.0,
            raw_output=data,
        )


class EasyOCREngine(OCREngine):
    """EasyOCR — PyTorch-based, good accuracy on real-world images."""

    name = "easyocr"

    def __init__(self):
        self._reader = None

    @property
    def reader(self):
        if self._reader is None:
            import easyocr
            self._reader = easyocr.Reader(["en"], gpu=False)
        return self._reader

    def read_plate(self, image_path: str) -> OCRResult:
        results = self.reader.readtext(image_path)

        if not results:
            return OCRResult(
                engine=self.name, text="", confidence=0.0, raw_output={}
            )

        # Concatenate all detected text regions
        text = "".join(r[1] for r in results)
        avg_conf = sum(r[2] for r in results) / len(results)

        return OCRResult(
            engine=self.name,
            text=text,
            confidence=avg_conf,
            raw_output={"detections": results},
        )


class PaddleOCREngine(OCREngine):
    """PaddleOCR — high accuracy, different architecture from PyTorch-based engines."""

    name = "paddleocr"

    def __init__(self):
        self._ocr = None

    @property
    def ocr(self):
        if self._ocr is None:
            from paddleocr import PaddleOCR
            self._ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
        return self._ocr

    def read_plate(self, image_path: str) -> OCRResult:
        result = self.ocr.ocr(image_path, cls=True)

        if not result or not result[0]:
            return OCRResult(
                engine=self.name, text="", confidence=0.0, raw_output={}
            )

        lines = result[0]
        text = "".join(line[1][0] for line in lines)
        avg_conf = sum(line[1][1] for line in lines) / len(lines)

        return OCRResult(
            engine=self.name,
            text=text,
            confidence=avg_conf,
            raw_output={"lines": result},
        )


# Registry of available engines
ENGINES = {
    "tesseract": TesseractEngine,
    "easyocr": EasyOCREngine,
    "paddleocr": PaddleOCREngine,
}


def get_engine(name: str, **kwargs) -> OCREngine:
    """Get an OCR engine by name."""
    if name not in ENGINES:
        raise ValueError(f"Unknown engine: {name}. Available: {list(ENGINES.keys())}")
    return ENGINES[name](**kwargs)


def get_all_engines() -> list[OCREngine]:
    """Instantiate all available OCR engines."""
    engines = []
    for name, cls in ENGINES.items():
        try:
            engines.append(cls())
        except Exception:
            pass  # Skip engines that can't be loaded
    return engines
