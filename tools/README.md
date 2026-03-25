# /tools

Working code, test harnesses, and scripts for the FlockBlocker adversarial testing pipeline.

## Implemented

- **OCR engine abstraction** (`ocr_engines.py`) — Unified interface for Tesseract, EasyOCR, and PaddleOCR with normalized confidence scoring
- **Plate compositor** (`plate_compositor.py`) — Generates synthetic plate images and composites with adversarial decals at configurable positions, distances, angles, IR wavelengths (850nm/940nm), and motion blur
- **Test suite** (`tests/`) — Pytest-based framework with baseline OCR accuracy tests, character confusion pair analysis, decal effect measurement, IR simulation, and cross-engine transferability evaluation
- **Fixtures structure** (`fixtures/`) — Organized directories for plate images, decal designs, and composite outputs

## Planned

- Adversarial patch generator for producing optimized bumper sticker candidates
- FOIA request generator for Flock Safety contracts by municipality
- Flock deployment mapper using public contract records
