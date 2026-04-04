"""
PDF and PNG output generation for Avery 5163 label stock.

Avery 5163 specs:
- Sheet: 8.5" x 11" (US Letter)
- Labels: 2" x 4", 10 per sheet (2 columns x 5 rows)
- Margins: 0.15625" top/bottom, 0.21875" left/right (approximate)
- Gap between labels: ~0.125" vertical, ~0.1875" horizontal
"""

import io
from pathlib import Path
from typing import Sequence

from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from . import RESEARCH_FOOTER

# Avery 5163 dimensions
SHEET_W, SHEET_H = letter  # 612 x 792 points
LABEL_W = 4.0 * inch
LABEL_H = 2.0 * inch
COLS = 2
ROWS = 5
LABELS_PER_SHEET = COLS * ROWS

# Margins and gaps (empirically matched to Avery 5163 template)
MARGIN_LEFT = 0.21875 * inch
MARGIN_TOP = 0.5 * inch
GAP_H = 0.1875 * inch  # horizontal gap between columns
GAP_V = 0.0 * inch  # vertical gap between rows (Avery 5163 has ~0 gap)


def _label_position(index: int) -> tuple[float, float]:
    """Get (x, y) position for label at given index (0-9) on sheet.

    Returns bottom-left corner in reportlab coordinates (origin at bottom-left).
    """
    col = index % COLS
    row = index // COLS
    x = MARGIN_LEFT + col * (LABEL_W + GAP_H)
    # reportlab y goes bottom-up; row 0 is top of sheet
    y = SHEET_H - MARGIN_TOP - (row + 1) * LABEL_H - row * GAP_V
    return x, y


def generate_pdf(
    images: Sequence[Image.Image],
    output_path: str,
    metadata: dict | None = None,
) -> str:
    """
    Generate a print-ready PDF with sticker images laid out on Avery 5163 sheets.

    Args:
        images: Sticker images to place (will fill sheets, 10 per sheet)
        output_path: Path to write PDF
        metadata: Optional metadata dict to embed in PDF properties

    Returns:
        Path to generated PDF
    """
    output_path = str(Path(output_path).with_suffix(".pdf"))
    c = canvas.Canvas(output_path, pagesize=letter)

    # Set PDF metadata
    c.setTitle("FlockBlocker Adversarial OCR Research Decals")
    c.setAuthor("FlockBlocker Project — flockblocker.org")
    c.setSubject("Adversarial ALPR Research Artifacts")
    c.setKeywords("adversarial ML, OCR, ALPR, research, FlockBlocker, BIRDSTRIKE")
    if metadata:
        c.setCreator(f"FlockBlocker Sticker Generator v1.0 | {metadata.get('strategy', 'unknown')}")

    for i, img in enumerate(images):
        if i > 0 and i % LABELS_PER_SHEET == 0:
            _add_sheet_footer(c)
            c.showPage()

        idx_on_sheet = i % LABELS_PER_SHEET
        x, y = _label_position(idx_on_sheet)

        # Convert PIL image to reportlab-compatible format
        img_rgba = img.convert("RGBA")
        buf = io.BytesIO()
        img_rgba.save(buf, format="PNG")
        buf.seek(0)

        from reportlab.lib.utils import ImageReader

        reader = ImageReader(buf)
        c.drawImage(reader, x, y, width=LABEL_W, height=LABEL_H, mask="auto")

        # Draw light cut-line border
        c.setStrokeColorRGB(0.85, 0.85, 0.85)
        c.setLineWidth(0.25)
        c.rect(x, y, LABEL_W, LABEL_H, stroke=1, fill=0)

    _add_sheet_footer(c)
    c.save()
    return output_path


def _add_sheet_footer(c: canvas.Canvas) -> None:
    """Add research attribution footer to current page."""
    c.setFont("Helvetica", 6)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawCentredString(SHEET_W / 2, 0.3 * inch, RESEARCH_FOOTER)


def generate_png(
    image: Image.Image,
    output_path: str,
) -> str:
    """
    Save a single sticker image as a high-resolution PNG.

    Args:
        image: Sticker image
        output_path: Path to write PNG

    Returns:
        Path to generated PNG
    """
    output_path = str(Path(output_path).with_suffix(".png"))
    # Set DPI metadata for print sizing
    image.save(output_path, dpi=(300, 300))
    return output_path


def generate_label_sheet_png(
    images: Sequence[Image.Image],
    output_path: str,
) -> str:
    """
    Generate a full Avery 5163 sheet as a single PNG (for preview).

    Args:
        images: Up to 10 sticker images
        output_path: Path to write PNG

    Returns:
        Path to generated PNG
    """
    # 8.5" x 11" at 300 DPI
    sheet_w = int(8.5 * 300)
    sheet_h = int(11 * 300)
    sheet = Image.new("RGBA", (sheet_w, sheet_h), (255, 255, 255, 255))

    label_w = int(4.0 * 300)
    label_h = int(2.0 * 300)
    margin_left = int(0.21875 * 300)
    margin_top = int(0.5 * 300)
    gap_h = int(0.1875 * 300)

    for i, img in enumerate(images[:LABELS_PER_SHEET]):
        col = i % COLS
        row = i // COLS
        x = margin_left + col * (label_w + gap_h)
        y = margin_top + row * label_h

        resized = img.resize((label_w, label_h), Image.LANCZOS)
        sheet.paste(resized, (x, y), resized if resized.mode == "RGBA" else None)

    output_path = str(Path(output_path).with_suffix(".png"))
    sheet.save(output_path, dpi=(300, 300))
    return output_path
