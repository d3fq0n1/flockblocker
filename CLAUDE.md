# FlockBlocker — Codebase Summary for Meta-Analysis

## What This Project Is

FlockBlocker is a multi-disciplinary research project targeting **data-layer vulnerabilities** in Flock Safety's automated license plate recognition (ALPR) system. Rather than obscuring plates (failed reads are discarded), it generates **confident misreads** that get stored as ground truth in Flock's database, corrupting pattern-of-life analysis, degrading alert reliability, and undermining prosecutorial use of the data.

**Key stats:** ~84 files, ~21 directories, ~4.0 MB, 75+ commits.

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Research/ML | Python 3, PyTorch, OpenCV, Pillow, NumPy, scikit-image |
| OCR Engines | Tesseract, EasyOCR, PaddleOCR (ensemble testing) |
| Backend | Cloudflare Workers (JavaScript), Cloudflare KV |
| Frontend | Vanilla HTML5/CSS3/JS (no framework), Google Fonts, Leaflet/OpenStreetMap |
| Testing | pytest, pytest-html, pytest-cov |
| Deployment | GitHub Pages (static) + Cloudflare Workers (serverless) |
| PDF Output | ReportLab (Avery 5163 label format) |
| Maps | Leaflet.js + CartoDB dark tiles (no API key) |

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
│   └── tests/              # pytest suite (9 modules)
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
├── eyesonme.html           # EYESONME operations dashboard (stations, subjects, FOIA, encryption)
├── doctrine.html           # Deterrence doctrine — standalone formal publication w/ SHA256
├── 404.html                # Custom 404 page
├── eyesonme-data.json      # Station fleet data (3 stations)
├── eyesonme-subjects.json  # Accountability subject profiles (9 subjects)
├── submit.html             # Story submission form
├── stories.html            # Approved user stories (geography-grouped)
├── evidence.html           # Public record contract & chief's response
├── birdstrike.html         # "Project BIRDSTRIKE" municipal research template
├── censorship.html         # Flock surveillance/censorship documentation
├── wall-of-shame.html      # Documented cases of Flock infrastructure misuse (stalking, voyeurism, predation)
├── money.html              # Flock Safety funding & grant mechanisms
├── rebellion.html          # Tracking 30+ municipal defections (NPR-sourced)
├── who.html                # Named officials & corporate officers
└── README.md               # Mission statement & overview
```

---

## Core Components

### 1. Adversarial Decal Research (6 Attack Strategies)

| Strategy | Mechanism | Key Idea |
|----------|-----------|----------|
| **Character Ambiguity** (`character_ambiguity`) | Font-weight/stroke manipulation at OCR confidence boundary | Exploits pairs like 0/O/D/Q, 1/I/L, 8/B, 5/S |
| **Retroreflective Interference** (`retroreflective`) | Geometric patterns (chevron, diamond, concentric) with IR-reactive materials | Physical-layer optical interference at 850/940nm wavelengths |
| **Boundary Noise** (`boundary_noise`) | Extends plate boundary into sticker region | OCR reads extra characters from adjacent sticker |
| **IR Phantom Injection** (`ir_phantom`) | Color pairs that collapse under 850nm/940nm IR | Visually distinct to humans, identical to IR cameras |
| **EOT Adversarial Patch** (`eot_adversarial`) | Gradient-optimized patterns (Expectation Over Transformation) | Robust to angle, distance (10-50 ft), lighting, printing |
| **Ensemble EOT** (`ensemble_eot`) | Hybrid white-box/black-box multi-engine optimization | Weighted aggregation across 3 OCR architectures for max transferability |

**Package-to-strategy matrix** (each package implements an intentional subset):

| Strategy | `sticker_gen/` (print-ready) | `tools/` (research pipeline) |
|---|:---:|:---:|
| `character_ambiguity` | ✓ | ✓ |
| `retroreflective` | ✓ | — (not an OCR attack) |
| `boundary_noise` | ✓ | ✓ |
| `ir_phantom` | — (research-only) | ✓ |
| `eot_adversarial` | — (research-only) | ✓ |
| `ensemble_eot` | — (research-only) | ✓ (in `ensemble_eot.py`) |

- `sticker_gen/` produces PNGs + Avery 5163 PDFs at 300 DPI. Restricted to strategies that actually make sense as a printed bumper sticker.
- `tools/` is the OCR research/evaluation pipeline. Restricted to strategies testable against OCR engines; physical retroreflective interference is out of scope.
- `CONFUSION_PAIRS` dict is canonical in `tools/decal_generator.py` and mirrored verbatim in `sticker_gen/strategies.py` — sync enforced by `TestCrossPackageSync` in `tools/tests/test_decal_generator.py`.

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

### 8. EYESONME Public Accountability Network (`eyesonme.html`)

Physical camera network mirroring Flock Safety's deployment methodology back at the officials who authorized it. Dashboard at `eyesonme.html`, data in JSON files.

**Dashboard sections:**
- **Network status bar**: deployed/active station counts, total runtime, motion events, network launch date
- **Station grid**: 3 station cards (Alpha/Bravo/Charlie) with status badges, target facility/official, battery/storage gauges, snapshot placeholders, field collection timestamps, `[ PROTECTED OPERATION ]` banners
- **Accountability subjects**: 9 dossier cards (3 municipal, 1 county, 1 state, 4 corporate) with status badges, silence counters, activity timelines, FOIA request tracking, document vaults
- **FOIA tracker**: Table with request ID, target agency, filed date, statutory deadline, status badges, overdue day counters
- **Activity feed**: Reverse-chronological network-wide event log
- **Encryption architecture**: 5-layer documentation (storage, transit, application, field collection, auth material) + seizure resistance
- **Deploy In Your City**: Full BOM (11 components, ~$355–585/station), 6-step setup sequence, legal checklist
- **Station map**: Leaflet/OpenStreetMap with CartoDB dark tiles, approximate Mauston-area markers

**Station hardware per unit:** Raspberry Pi 5, DietPi, RPi Camera Module 3 (IR), Waveshare SIM7600 4G LTE, LiFePO4 battery, MPPT solar, SX1276 LoRa 915MHz + ESP32 local radio, IP65 enclosure with tamper sensor.

**Field collection flow:** LoRa TOTP auth → ESP32 activates hidden WPA3 AP → encrypted data pull → AP shutdown → radio-silent.

### 9. Deterrence Doctrine (`doctrine.html`)

Published deterrence doctrine — formal dated document with live SHA-256 hash (computed via Web Crypto API), operator/date metadata, legal citations. Rendered site-wide:
- `[ DETERRENCE DOCTRINE ]` link in every page header
- Condensed doctrine text in every page footer
- EYESONME section header with doctrine reference
- `[ PROTECTED OPERATION ]` banners on station cards
- FOIA tracker header note
- Standalone `/doctrine` page

### 10. Public Information Pages

Static HTML pages documenting the Wall of Shame (verified misuse cases), municipal defections, FOIA templates, the "Project BIRDSTRIKE" distributed research framework, evidence/contracts, funding analysis, censorship documentation, and personnel dossiers.

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

### EYESONME Station Data (`eyesonme-data.json`)
```json
{
  "network": { "launch_date", "operator", "legal_basis", "total_runtime_hours", "total_motion_events" },
  "stations": [{
    "id": "EYESONME-001", "name", "target_facility", "target_official",
    "location_description", "coordinates": { "lat", "lng" },
    "status": "PLANNED|ACTIVE|OFFLINE|DEGRADED",
    "hardware": { "compute", "os", "camera", "cellular", "battery", "solar", "storage", "enclosure", "local_radio" },
    "last_heartbeat", "battery_pct", "battery_voltage", "solar_input_watts",
    "uptime_seconds", "last_snapshot_url", "motion_events_today",
    "storage_free_pct", "signal_strength", "last_collection", "pending_collection",
    "events": []
  }]
}
```

### EYESONME Subjects (`eyesonme-subjects.json`)
```json
{
  "subjects": [{
    "id": "zilisch-michael", "name", "title", "org", "org_type": "MUNICIPAL|COUNTY|STATE|CORPORATE",
    "role_in_lpr", "status": "UNRESPONSIVE|RESPONDED|UNDER REVIEW|ESCALATED",
    "last_activity", "silence_start", "silence_broken", "station_id",
    "timeline": [{ "date", "type": "FOIA|STATEMENT|MEETING|SILENCE|ESCALATION", "description" }],
    "foia_requests": [{ "id", "filed", "target", "subject", "statutory_deadline", "status" }],
    "documents": [{ "title", "type", "status": "OBTAINED|PENDING", "url" }]
  }]
}
```
Silence counters and FOIA overdue counters compute live in the browser from these dates.

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
11. **Symmetric accountability**: EYESONME mirrors Flock Safety's own methodology — cameras in public spaces, dashboard interface, fleet management — directed at the officials who authorized surveillance.
12. **Data-driven UI**: EYESONME dashboard renders entirely from JSON data files — update station/subject data without touching HTML/JS.
13. **Deterrence as architecture**: Published doctrine with cryptographic witness (SHA-256), present on every page — ambient, not aggressive.
14. **5-layer encryption**: LUKS2 at rest, WireGuard in transit, application-layer public-key encryption, WPA3 field collection, LUKS-protected auth material. Seizure-resistant by design.
15. **Offshore data sovereignty**: VPS outside US jurisdiction (Iceland/Switzerland/Netherlands). No US cloud providers in data path.

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
- EYESONME station IDs: `EYESONME-001` (Alpha), `EYESONME-002` (Bravo), `EYESONME-003` (Charlie)
- EYESONME status values: `PLANNED`, `ACTIVE`, `OFFLINE`, `DEGRADED`
- Subject org types: `MUNICIPAL`, `COUNTY`, `STATE`, `CORPORATE`
- Subject status values: `UNRESPONSIVE`, `RESPONDED`, `UNDER REVIEW`, `ESCALATED`
- FOIA status values: `FILED`, `OVERDUE`, `PARTIALLY FULFILLED`, `FULFILLED`, `DENIED`
- Timeline event types: `FOIA`, `STATEMENT`, `MEETING`, `SILENCE`, `ESCALATION`
- Color coding: green (`#4af0a0`) = EYESONME/active, amber (`#f0a84a`) = BirdStrike/warning, red (`#f05a4a`) = evidence/overdue, lime (`#c8f04a`) = default accent
- Deterrence doctrine footer present on every HTML page site-wide
- `[ DETERRENCE DOCTRINE ]` header link present on every HTML page
- All pages link to `eyesonme.html` and `doctrine.html` in both desktop and mobile navigation
