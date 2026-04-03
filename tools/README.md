# /tools

Working code, test harnesses, and scripts for the FlockBlocker adversarial testing pipeline.

## Implemented

- **OCR engine abstraction** (`ocr_engines.py`) — Unified interface for Tesseract, EasyOCR, and PaddleOCR with normalized confidence scoring across all three backends
- **Plate compositor** (`plate_compositor.py`) — Generates synthetic plate images and composites with adversarial decals at configurable positions, distances, angles, IR wavelengths (850nm/940nm), and motion blur levels
- **Test suite** (`tests/`) — Pytest-based framework: baseline OCR accuracy, character confusion pair analysis, decal effect measurement, IR simulation, cross-engine transferability evaluation
- **Fixtures** (`fixtures/`) — Organized directories for plate images, decal designs, and composite outputs

## Planned

- Adversarial patch generator — EOT-optimized bumper sticker candidate production
- FOIA request generator — templated requests for Flock Safety contracts by municipality
- Flock deployment mapper — visualization of camera locations using public contract records
