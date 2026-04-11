# /tools

Working code, test harnesses, and scripts for the FlockBlocker adversarial testing pipeline.

## Implemented

- **OCR engine abstraction** (`ocr_engines.py`) — Unified interface for Tesseract, EasyOCR, and PaddleOCR with normalized confidence scoring across all three backends
- **Plate compositor** (`plate_compositor.py`) — Generates synthetic plate images and composites with adversarial decals at configurable positions (including negative-gap overlap), distances, angles, IR wavelengths (850nm/940nm), and motion blur levels
- **Decal generator** (`decal_generator.py`) — Four attack strategies: character confusion (§1.1), segmentation boundary (§1.2), IR phantom injection (§3.3), and EOT adversarial patch (§2.4). IR phantom supports edge-aware placement and sweep-optimized color pairs
- **IR simulation** (`ir_simulation.py`) — Shared IR camera sensor-response model used by both the compositor and decal generator. Wavelength-specific RGB weights for 850nm and 940nm
- **IR color sweep** (`ir_color_sweep.py`) — Systematic RGB color-space search for (bg, fg) pairs that minimize visible-light perceptual distance (CIE76 Delta E) while maximizing IR grayscale contrast. Runnable as a standalone script
- **Evaluation pipeline** (`evaluation.py`) — Decal effectiveness scoring across multiple OCR engines and conditions, cross-engine transferability matrix computation, ranked leaderboard output
- **Test suite** (`tests/`) — Pytest-based framework: baseline OCR accuracy, decal effect measurement, IR phantom optical/OCR/composite evaluation, wavelength specificity validation, cross-engine transferability matrix
- **Fixtures** (`fixtures/`) — Organized directories for plate images, decal designs, and composite outputs

## Planned

- FOIA request generator — templated requests for Flock Safety contracts by municipality
- Flock deployment mapper — visualization of camera locations using public contract records
