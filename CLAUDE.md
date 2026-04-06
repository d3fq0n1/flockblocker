# FlockBlocker — Codebase Summary for Meta-Analysis

## What This Project Is

FlockBlocker is a multi-disciplinary research project targeting **data-layer vulnerabilities** in Flock Safety's automated license plate recognition (ALPR) system. Rather than obscuring plates (failed reads are discarded), it generates **confident misreads** that get stored as ground truth in Flock's database, corrupting pattern-of-life analysis, degrading alert reliability, and undermining prosecutorial use of the data.

**Key stats:** 175+ files, 100+ directories, 3.5+ MB, 550+ commits.

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Research/ML | Python 3, PyTorch, OpenCV, Pillow, NumPy, scikit-image |
| OCR Engines | Tesseract, EasyOCR, PaddleOCR (ensemble testing) |
| Backend | Cloudflare Workers (JavaScript), Cloudflare KV |
| Frontend | Vanilla HTML5/CSS3/JS (no framework), Google Fonts |
| Testing | pytest, pytest-html, pytest-cov |
| Deployment | GitHub Pages (static) + Cloudflare Workers (serverless) |
| PDF Output | ReportLab (Avery 5163 label format) |

---

## Project Structure

```
flockblocker/
├── tools/                  # OCR testing & evaluation pipeline (Python)
│   ├── ocr_engines.py      # Unified Tesseract/EasyOCR/PaddleOCR interface
│   ├── plate_compositor.py # Synthetic plate + decal compositing (perspective warp)
│   ├── plate_formats.py    # All 50 states + DC plate format rules
│   ├── decal_generator.py  # 4 attack strategy implementations
│   ├── ensemble_eot.py     # Hybrid white-box/black-box ensemble EOT optimizer
│   ├── ir_simulation.py    # NIR sensor response simulation
│   ├── ir_color_sweep.py   # Optimize phantom color pairs
│   ├── evaluation.py       # Effectiveness scoring & metrics
│   ├── foia_ingest.py      # FOIA image ingestion & benchmarking pipeline
│   └── tests/              # pytest suite (10 modules)
│       ├── test_ocr_baseline.py
│       ├── test_decal_effect.py
│       ├── test_ir_phantom.py
│       ├── test_decal_generator.py
│       ├── test_transferability_matrix.py
│       ├── test_plate_formats.py
│       ├── test_perspective.py
│       ├── test_ensemble_eot.py
│       └── test_foia_ingest.py
│
├── sticker_gen/            # Standalone adversarial decal generator
│   ├── __main__.py         # CLI entry point
│   ├── generator.py        # Main generation logic
│   ├── strategies.py       # Strategy implementations
│   ├── pdf_output.py       # Avery 5163 PDF rendering
│   └── requirements.txt
│
├── worker/                 # Cloudflare Workers backend
│   ├── worker.js           # Story submission/moderation API
│   └── wrangler.toml       # CF deployment config
│
├── research/               # Academic papers & vulnerability docs
├── adversarial/            # Adversarial patch research
├── hardware/               # Raspberry Pi & Public Accountability Station specs
├── optical/                # IR interference & retroreflective material research
├── distribution/           # Bumper sticker designs & distribution strategy
├── legal/                  # FOIA templates & contract analysis
├── prompts/                # System prompts for Gemini Nano on-device intelligence
├── screenshots/            # Media assets
│
├── index.html              # Homepage with statistics & mission
├── submit.html             # Story submission form
├── stories.html            # Approved user stories (geography-grouped)
├── birdstrike.html         # "Project BIRDSTRIKE" municipal research template
├── censorship.html         # Flock surveillance/censorship documentation
├── harms.html              # Catalog of Flock negative impacts
├── rebellion.html          # Tracking 32+ municipal defections
├── who.html                # Project maintainers
└── README.md               # Mission statement & overview
```

---

## Core Components

### 1. Adversarial Decal Research (4 Attack Strategies)

| Strategy | Mechanism | Key Idea |
|----------|-----------|----------|
| **Character Confusion** | Font-weight/stroke manipulation at OCR confidence boundary | Exploits pairs like 0/O/D/Q, 1/I/L, 8/B, 5/S |
| **Segmentation Boundary** | Extends plate boundary into sticker region | OCR reads extra characters from adjacent sticker |
| **IR Phantom Injection** | Color pairs that collapse under 850nm/940nm IR | Visually distinct to humans, identical to IR cameras |
| **EOT Adversarial Patch** | Gradient-optimized patterns (Expectation Over Transformation) | Robust to angle, distance (10-50 ft), lighting, printing |
| **Ensemble EOT** | Hybrid white-box/black-box multi-engine optimization | Weighted aggregation across 3 OCR architectures for max transferability |

### 2. Sticker Generator (`sticker_gen/`)

CLI tool producing print-ready adversarial decals:
```bash
python -m sticker_gen --plate ABC1234 --strategy all --variants 2 --output ./stickers
```
Outputs: individual PNGs (300 DPI), Avery 5163 PDF sheets, JSON manifest with UUIDs.

### 3. OCR Evaluation Pipeline (`tools/`)

Tests decals against 3 OCR engines across 9 capture conditions:
- Ideal (20 ft, 0deg), Mid-range (35 ft), Far (50 ft)
- Angled yaw (25 ft, 15deg yaw), Angled yaw+pitch (25 ft, 8deg yaw, 10deg pitch)
- Motion blur (25 ft, 8px)
- IR 850nm, IR 940nm, Worst-case (45 ft, 10deg yaw, 5deg pitch, 5px blur)

Perspective simulation uses 3D homography (yaw = roadside camera offset, pitch = pole-mount downward angle).

Produces: misread rates, plausible misread rates (validated against 50-state plate formats), confidence deltas, cross-engine transferability matrices.

### 4. Story Submission System (`worker/`)

Citizen-impact documentation via Cloudflare Workers + KV:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/submit` | POST | Submit story (state, city, story, optional name/email) |
| `/api/stories` | GET | Retrieve approved stories |
| `/admin` | GET | Password-protected moderation dashboard |
| `/api/admin/pending` | GET | List pending submissions |
| `/api/admin/moderate` | POST | Approve/reject submissions |

### 5. Plate Format Rules (`tools/plate_formats.py`)

Structured plate format definitions for all 50 US states + DC:
- Generation: produce random valid plates for any state
- Validation: check if a string matches any state's plate format
- Constraint: ensure adversarial misreads are plausible (would survive Flock's validation)
- Confusion-aware: generate plates maximally loaded with confusable characters
- Misread enumeration: find all 1-2 character confusion substitutions that remain plausible

### 6. Ensemble EOT Optimizer (`tools/ensemble_eot.py`)

Hybrid multi-engine adversarial patch optimization:
- **White-box**: Differentiable proxy losses for EasyOCR (CRNN) and PaddleOCR (Transformer) with engine-specific weight profiles
- **Black-box**: SPSA gradient estimation for Tesseract (no gradient path)
- **Aggregation**: Weighted max (minimax — optimize against hardest-to-fool engine) or weighted mean
- Per-engine configurable weights for transferability tuning
- Full EOT: random angle/scale/brightness transforms per step

### 7. FOIA Image Ingestion (`tools/foia_ingest.py`)

Pipeline for real Flock camera captures obtained through public records requests:
- **Ingest**: Scan directories, compute file hashes, create catalog
- **Normalize**: Crop, resize, contrast-enhance, optional grayscale
- **Label**: OCR-assisted ground-truth labeling (human verifies)
- **Benchmark**: Measure engine accuracy against ground-truth labels
- **Placeholders**: Synthetic captures for pipeline testing until real images arrive

### 8. Public Information Pages

Static HTML pages documenting surveillance harms, municipal defections, FOIA templates, and the "Project BIRDSTRIKE" distributed research framework.

---

## Data Models

### Cloudflare KV (Stories)
```
submission:{uuid}  → {id, state, city, story, display_name, email, ip_hash, timestamp, status}
index:pending      → [uuid, ...]
index:approved     → [uuid, ...]
```
IP addresses are SHA-256 hashed (truncated 16 hex chars) — raw IPs never stored.

### Sticker Manifest (JSON)
Each generation run produces a manifest with `run_id`, `plate_text`, seed, tool version, and per-sticker metadata (strategy, dimensions, DPI, output files).

### Evaluation Results
`SingleResult` dataclass: engine, condition, plate text, clean/decal reads, clean/decal confidence, plausibility check against 50-state plate formats.
`DecalScore`: aggregated misread rate, plausible misread rate, and transferability across engines.

### FOIA Catalog (JSON)
```
catalog.json → {catalog_id, created_at, agency, images: [{image_id, source_file, ground_truth, state, ...}]}
```
Each image entry tracks source hash (integrity), OCR-assisted labeling, and researcher notes.

---

## Key Design Decisions

1. **Data-layer, not optical**: Failed reads are discarded; confident misreads persist as ground truth.
2. **Ensemble transferability**: Testing against 3 different OCR architectures (not just one) increases confidence that attacks exploit fundamental weaknesses.
3. **Hybrid optimization**: White-box gradients through differentiable engines + black-box SPSA estimation for non-differentiable engines, with weighted aggregation.
4. **Plausibility constraints**: Misreads validated against all 50-state plate formats — only format-valid misreads survive Flock's pipeline into the database.
5. **Physical-world robustness**: Perspective warp (yaw + pitch homography), distance degradation, motion blur, IR simulation across all capture conditions.
6. **Manifest-driven pipeline**: Every artifact gets a UUID and JSON metadata for reproducibility and distributed research.
7. **No traditional database**: Cloudflare KV for simplicity; IP hashing for privacy.
8. **Academic rigor**: Seeds, fixtures, condition sets, transferability matrices, citations to CVPR/NeurIPS/ICML papers.
9. **Legal positioning**: Research publication (First Amendment), no physical tampering, no computer system access, full attribution on all outputs.
10. **FOIA-ready**: Ingestion pipeline prepared for real camera captures — normalize, label, benchmark against ground truth.

---

## Running the Project

```bash
# OCR testing
pip install -r tools/requirements.txt
cd tools && pytest -v

# Sticker generation
pip install -r sticker_gen/requirements.txt
python -m sticker_gen --plate ABC1234 --output ./stickers

# Deploy story backend
cd worker
wrangler kv namespace create SUBMISSIONS
wrangler secret put ADMIN_PASSWORD
wrangler deploy
```

---

## Conventions

- Strategy names: `character_ambiguity`, `retroreflective`, `boundary_noise`, `ir_phantom`, `eot_adversarial`, `ensemble_eot`
- Test plates: WI-based, confusion-heavy (`BOO8008`, `ILL1100`, `SGS5255`)
- IR wavelengths: 850nm (red-heavy), 940nm (flatter) matching common Flock camera specs
- Perspective angles: yaw (horizontal/roadside) and pitch (vertical/pole-mount) in degrees
- Plate format validation: all generated/misread plates checked against 50-state format rules
- All generated outputs include research attribution footer
