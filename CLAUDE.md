# FlockBlocker — Codebase Summary for Meta-Analysis

## What This Project Is

FlockBlocker is a multi-disciplinary research project targeting **data-layer vulnerabilities** in Flock Safety's automated license plate recognition (ALPR) system. Rather than obscuring plates (failed reads are discarded), it generates **confident misreads** that get stored as ground truth in Flock's database, corrupting pattern-of-life analysis, degrading alert reliability, and undermining prosecutorial use of the data.

**Key stats:** 166 files, 99 directories, 3.0 MB, 546+ commits.

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
│   ├── plate_compositor.py # Synthetic plate + decal image compositing
│   ├── decal_generator.py  # 4 attack strategy implementations
│   ├── ir_simulation.py    # NIR sensor response simulation
│   ├── ir_color_sweep.py   # Optimize phantom color pairs
│   ├── evaluation.py       # Effectiveness scoring & metrics
│   └── tests/              # pytest suite (6 modules)
│       ├── test_ocr_baseline.py
│       ├── test_decal_effect.py
│       ├── test_ir_phantom.py
│       ├── test_decal_generator.py
│       ├── test_transferability_matrix.py
│       └── conftest.py
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

### 2. Sticker Generator (`sticker_gen/`)

CLI tool producing print-ready adversarial decals:
```bash
python -m sticker_gen --plate ABC1234 --strategy all --variants 2 --output ./stickers
```
Outputs: individual PNGs (300 DPI), Avery 5163 PDF sheets, JSON manifest with UUIDs.

### 3. OCR Evaluation Pipeline (`tools/`)

Tests decals against 3 OCR engines across 8 capture conditions:
- Ideal (20 ft, 0deg), Mid-range (35 ft), Far (50 ft)
- Angled (25 ft, 15deg), Motion blur (25 ft, 8px)
- IR 850nm, IR 940nm, Worst-case (45 ft, 10deg, 5px blur)

Produces: misread rates, confidence deltas, cross-engine transferability matrices.

### 4. Story Submission System (`worker/`)

Citizen-impact documentation via Cloudflare Workers + KV:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/submit` | POST | Submit story (state, city, story, optional name/email) |
| `/api/stories` | GET | Retrieve approved stories |
| `/admin` | GET | Password-protected moderation dashboard |
| `/api/admin/pending` | GET | List pending submissions |
| `/api/admin/moderate` | POST | Approve/reject submissions |

### 5. Public Information Pages

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
`SingleResult` dataclass: engine, condition, plate text, clean/decal reads, clean/decal confidence.
`DecalScore`: aggregated misread rate and transferability across engines.

---

## Key Design Decisions

1. **Data-layer, not optical**: Failed reads are discarded; confident misreads persist as ground truth.
2. **Ensemble transferability**: Testing against 3 different OCR architectures (not just one) increases confidence that attacks exploit fundamental weaknesses.
3. **Physical-world robustness**: All patterns must survive printing at bumper-sticker scale across real-world capture conditions.
4. **Manifest-driven pipeline**: Every artifact gets a UUID and JSON metadata for reproducibility and distributed research.
5. **No traditional database**: Cloudflare KV for simplicity; IP hashing for privacy.
6. **Academic rigor**: Seeds, fixtures, condition sets, transferability matrices, citations to CVPR/NeurIPS/ICML papers.
7. **Legal positioning**: Research publication (First Amendment), no physical tampering, no computer system access, full attribution on all outputs.

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

- Strategy names: `character_ambiguity`, `retroreflective`, `boundary_noise`, `ir_phantom`, `eot_adversarial`
- Test plates: WI-based, confusion-heavy (`BOO8008`, `ILL1100`, `SGS5255`)
- IR wavelengths: 850nm (red-heavy), 940nm (flatter) matching common Flock camera specs
- All generated outputs include research attribution footer
