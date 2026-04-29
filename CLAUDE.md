# FlockBlocker — Codebase Summary for Meta-Analysis

## What This Project Is

FlockBlocker is a multi-disciplinary research project targeting **data-layer vulnerabilities** in Flock Safety's automated license plate recognition (ALPR) system. Rather than obscuring plates (failed reads are discarded), it generates **confident misreads** that get stored as ground truth in Flock's database, corrupting pattern-of-life analysis, degrading alert reliability, and undermining prosecutorial use of the data.

**Key stats:** ~80 source files, ~20 directories, 4 MB.

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
├── legal/                  # FOIA templates, contract analysis, C&D transcription
│   ├── coordination/       # Email PDF exhibits cited from the-coordination.html
│   └── bouquet/            # Exhibit PDFs cited from the-bouquet.html
├── flockdocs/              # Primary-source documents (C&D PDF, contracts, journal entries, FOIA productions)
├── prompts/                # System prompts for Gemini Nano on-device intelligence
├── screenshots/            # Media assets
│
├── index.html              # Homepage with statistics & mission
├── eyesonme.html           # EYESONME operations dashboard (stations, subjects, FOIA, encryption)
├── doctrine.html           # Deterrence doctrine — standalone formal publication w/ SHA256
├── 404.html                # Custom 404 page
├── eyesonme-data.json      # Station fleet data (3 stations)
├── eyesonme-subjects.json  # Accountability subject profiles (8 subjects)
├── coordination-emails.json    # Email exhibit timeline data (drip-fed via status flips)
├── coordination-productions.json  # Open records production chain data
├── bouquet-findings.json   # Twelve municipal-record findings (procurement / fiduciary / process / disclosure / contractual)
├── bouquet-sources.json    # Production chain + Buehlman probate source list
├── submit.html             # Story submission form
├── stories.html            # Approved user stories (geography-grouped)
├── evidence.html           # Public record contract & chief's response
├── the-letter.html         # April 16 cease-and-desist as redaction-with-reveal performance
├── the-coordination.html   # Flock-City email record, JSON-driven drip-fed timeline
├── the-bouquet.html        # Twelve findings on city procurement and fiduciary record, JSON-driven
├── wall-of-shame.html      # Documented LPR-network misuse cases
├── birdstrike.html         # "Project BIRDSTRIKE" municipal research template
├── harms.html              # Catalog of Flock harms + censorship record + money flow (merged)
├── rebellion.html          # Tracking 32+ municipal defections
├── who.html                # Named officials & corporate officers
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

### 8. EYESONME Public Accountability Network (`eyesonme.html`)

Physical camera network mirroring Flock Safety's deployment methodology back at the officials who authorized it. Dashboard at `eyesonme.html`, data in JSON files.

**Dashboard sections:**
- **Network status bar**: deployed/active station counts, total runtime, motion events, network launch date
- **Station grid**: 3 station cards (Alpha/Bravo/Charlie) with status badges, target facility/official, battery/storage gauges, snapshot placeholders, field collection timestamps, `[ PROTECTED OPERATION ]` banners
- **Accountability subjects**: 8 dossier cards (3 municipal, 1 county, 4 corporate) with status badges, silence counters, activity timelines, FOIA request tracking, document vaults
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

### 10. The Letter (`the-letter.html`)

Cease-and-desist letter served by Flock Safety on April 16, 2026, published April 28, 2026 as a redaction-with-reveal performance piece — Day 1 of a staggered three-page rollout (Day 2 and Day 3 not yet built).

**Component behavior:**
- The procedural envelope (letterhead, date, service line, recipient block with the eight noticed email addresses, RE line, salutation, closing, Dan Haley signature, proof-of-service footer) renders unredacted.
- All 14 substantive paragraphs of demand and legal argument are wrapped in `<span class="redactable">` elements that render as solid black bars.
- Desktop: hover reveals; focus also reveals (keyboard accessible).
- Touch: tap to reveal; 4-second auto-conceal; immediate conceal on scroll-out (IntersectionObserver).
- Per-element timeouts isolated so adjacent spans don't interfere.
- "Reveal All" / "Conceal All" buttons at the top of the letter section override per-element behavior with a global lock.
- `<noscript>` block: redactions stay opaque if JS is disabled; download link to original PDF remains accessible.
- ARIA: `tabindex="0"`, `role="button"`, `aria-label="Redacted text — activate to reveal"`, `aria-live="polite"` on every redactable; hidden `.sr-only` preface announces redaction-by-design before the revealed text.

**Source artifacts:**
- Original PDF: `flockdocs/CEASE AND DESIST_Flockblocker.pdf`
- Verbatim transcription (canonical): `legal/cease-and-desist-2026-04-16.txt`
- Wayback snapshot link: April 16, 2026 15:29 ET (link in Status block)
- Git tag (operator-managed): `pre-cease-and-desist-2026-04-16`

**Tone constraint:** the-letter.html is the only page on the site where the campaign jokes. The joke is the design (redaction undone trivially) — the prose stays flat, dated, and procedural. No exclamation marks, no adjectives describing Flock's conduct, no mention of any city official, no preview of forthcoming page content beyond Section 5's single dated sentence.

**Not in nav.** The page is reachable from the homepage "Recent" section only, matching the existing out-of-nav pattern (`harms.html`, `doctrine.html`, `stories.html`, `submit.html`).

### 11. The Coordination (`the-coordination.html`)

JSON-driven timeline of Flock Safety ↔ City of Mauston email correspondence sourced from open records productions under Wis. Stat. § 19.35. Day 2 of the staggered three-page rollout. Day 1 (`the-letter.html`) is the signal; this page is the substance.

**Component behavior:**
- Page chrome (header, footer, nav) is identical to other site pages. Out of nav, like `the-letter.html`.
- Section 3 (email timeline) renders entirely from `coordination-emails.json` via vanilla `fetch().then()` — same loader pattern as `eyesonme.html`. Inline TOC built from the same data; deep-link anchors via `id="entry-<id>"`.
- Section 4 (production chain) renders from `coordination-productions.json`.
- Each entry has `status: "published"` or `status: "forthcoming"`. Forthcoming entries render as opacity-0.55 placeholder cards with a `[ PENDING PUBLICATION ]` exhibit-slot label and a single `Pending publication.` body line — no passages, attachments, or source footer.
- Display order = JSON array order (chronological by authoring; operator-controlled tie-breaking for same-day entries).
- Render-failure path: each fetch's `.catch()` injects an inline `.render-error` line so the section degrades visibly instead of silently.
- `<noscript>` block in Section 3 explains the page requires JavaScript and points readers at `legal/coordination/` for the raw PDFs.

**Drip-feed workflow** (lives in `coordination-emails.json`'s `operator_workflow` field and in `legal/coordination/README.md`):
1. Place email PDF at `legal/coordination/YYYY-MM-DD-shortname.pdf`.
2. Open `coordination-emails.json`, find entry by `id`.
3. Flip `status` from `forthcoming` to `published`; fill in `sender`, `recipients`, `subject`, `time`, `passages`, `attachments`, `source`.
4. Commit with message `Publish coordination entry: <id>`. Push.

No HTML edits, no JS edits, no CSS edits per drop. JSON + PDF only.

**Editorial register:** Inverse of `the-letter.html`. Page contains zero editorializing prose; documents speak. No adjectives describing Flock or city personnel. No exclamation marks. No mention of K9 fund / Buehlman estate / journal entries / fiduciary breach — that material is Day 3.

**Source artifacts seeded at launch:**
- One `published` entry: Gautam Ratnam (Account Executive, Flock Group, Inc.) → Daron J. Haugh + Michael Zilisch, CC Mike Wahl + Tina Maharath, April 9, 2026, 13:10 CT, Exhibit B, attaching `Flock talking points.pdf`. Two passages quoted verbatim. Source PDF placeholder at `legal/coordination/2026-04-09-gautam-talking-points.pdf` — operator drops in.
- Three `forthcoming` entries (April 16, April 16, April 17) seeded as placeholders.

**Cross-link from `the-letter.html`:** Section 5 ("What's next") of the Day 1 page now links the phrase "open records production" to this page. Single-paragraph, single-anchor edit; no copy added.

### 12. The Bouquet (`the-bouquet.html`)

JSON-driven page documenting twelve findings on the City of Mauston's procurement, authorization, and fiduciary record around its Flock Safety contract. Day 3 of the staggered three-page rollout. Day 1 (`the-letter.html`) is the signal; Day 2 (`the-coordination.html`) is the Flock-side substance; Day 3 is the city-side substance.

**Component behavior:**
- Page chrome (header, footer, nav) is identical to other pages. Out of nav.
- Section 3 renders entirely from `bouquet-findings.json` via vanilla `fetch().then()` — same loader pattern as `eyesonme.html` and `the-coordination.html`.
- Each finding renders as a card with: number, category badge, title, summary, statutes-cited block (where present), per-document blocks (label + optional blockquote with `cite=path` + download link or pending-placement marker), and a footer with see-also cross-references.
- Inline TOC built from the same data; deep-link anchors via `id="finding-N-slug"`.
- Category filter at top of Section 3: five buttons (`procurement`, `fiduciary`, `process`, `disclosure`, `contractual`) plus `All` reset, `aria-pressed` state, JS-driven `[hidden]` toggling on cards. No-JS = all visible.
- Section 4 (production chain + Buehlman probate) renders from `bouquet-sources.json`. `kind` field differentiates `city-production` (amber left border) from `probate` (lavender left border).
- Render-failure path: each fetch's `.catch()` injects an inline `.render-error` line.
- `<noscript>` block points readers at `bouquet-findings.json` and `legal/bouquet/`.

**Not drip-fed.** Unlike Day 2, all twelve findings are seeded as `status: "published"` at launch. Every finding rests on documents already produced by the city or already in the public probate record. Future updates are document additions to `documents` arrays (see operator workflow below), not status flips.

**Operator workflow** (also stored in `bouquet-findings.json`'s `operator_workflow` field and in `legal/bouquet/README.md`):
- Add finding: append to `findings` with the next sequential number; fill `summary`, `statutes_cited`, `documents`; place exhibit PDFs at `documents[].path`; commit `Add finding <N>: <title>`.
- Update finding: append to the entry's `documents` array (do not renumber); commit `Update finding <N>: <reason>`.

No HTML / JS / CSS edits per drop.

**Editorial register:** Same clinical posture as Day 2, with one stricter rule. The page asserts no legal conclusions. Statutes are cited; the record is stated; the reader concludes. No "embezzlement," "breach," "violation," "misappropriation," "corruption," or "fiduciary breach" language anywhere on the page. Phrasing pattern: "Wis. Stat. § X requires Y. The record shows Z."

**Source artifacts:**
- City of Mauston productions: April 20, April 23, and April 27, 2026 (three releases).
- Buehlman probate record: Juneau County Case No. 2022PR000027.
- Documents already in repo: `Flock Executed Agreement - Signed.pdf`, `Response to Clark, Blake.pdf`, `flockdocs/JE-24-015.pdf`, `flockdocs/JE-24-016.pdf`.
- Documents pending operator placement: see `legal/bouquet/README.md` for the full table.

**Cross-links:**
- `the-letter.html` Section 5 now links the phrase "analysis of municipal procurement and fiduciary process" to this page (the existing "open records production" → coordination anchor stays).
- `the-coordination.html` Section 5 links the phrase "procurement, authorization, and fiduciary record" to this page.
- This page's Section 5 links back to both `the-coordination.html` and `the-letter.html`.

**Pre-existing site content overlap.** Several findings are partially anticipated by older pages (`evidence.html` references Sgt. Brandon Arenz, the Section 5.3 disclosure issue, the estate-donation funding claim, and the council-authorization gap; `who.html` carries the Sgt. Arenz dossier). Those pages were intentionally left untouched in the Day 3 build. The bouquet is the consolidated, sourced version; older surface-level mentions remain as their own historical record.

### 13. Public Information Pages

Static HTML pages documenting surveillance harms, municipal defections, FOIA templates, the "Project BIRDSTRIKE" distributed research framework, evidence/contracts, funding analysis, censorship documentation, and personnel dossiers.

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
    "id": "zilisch-shawn", "name", "title", "org", "org_type": "MUNICIPAL|COUNTY|CORPORATE",
    "role_in_lpr", "status": "UNRESPONSIVE|RESPONDED|UNDER REVIEW|ESCALATED",
    "last_activity", "silence_start", "silence_broken", "station_id",
    "timeline": [{ "date", "type": "FOIA|STATEMENT|MEETING|SILENCE", "description" }],
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
- Subject status values: `UNRESPONSIVE`, `RESPONDED`, `UNDER REVIEW`, `ESCALATED`
- FOIA status values: `FILED`, `OVERDUE`, `PARTIALLY FULFILLED`, `FULFILLED`, `DENIED`
- Timeline event types: `FOIA`, `STATEMENT`, `MEETING`, `SILENCE`
- Color coding: green (`#4af0a0`) = EYESONME/active, amber (`#f0a84a`) = BirdStrike/warning, red (`#f05a4a`) = evidence/overdue, lime (`#c8f04a`) = default accent
- Deterrence doctrine footer present on every HTML page site-wide
- `[ DETERRENCE DOCTRINE ]` header link present on every HTML page
- All pages link to `eyesonme.html` and `doctrine.html` in both desktop and mobile navigation
- Pages outside the standardized nav: `harms.html`, `doctrine.html`, `stories.html`, `submit.html`, `the-letter.html`, `the-coordination.html`, `the-bouquet.html`, `404.html` — reachable from the homepage or contextual links only
- Redaction component: `.redactable` spans with click/focus reveal, 4-second auto-conceal, IntersectionObserver scroll-conceal, `prefers-reduced-motion` honored; `[ REVEAL ALL ]` / `[ CONCEAL ALL ]` controls override per-element behavior. Used only on `the-letter.html`.
- Editorial tone is clinical and procedural across the site — `the-letter.html` is the sole exception, where the joke lives in the design rather than the prose
- JSON-driven page rendering: `eyesonme.html` (stations + subjects), `the-coordination.html` (email exhibits + productions), `the-bouquet.html` (findings + sources). Pattern is `fetch('X.json').then(r => r.json()).then(render).catch(fail)` with inline-string `innerHTML` building. Page-specific styles inline in `<style>`; no shared `assets/js/` directory exists.
- `the-coordination.html` drip-feed: to publish a `forthcoming` entry, drop the PDF at `legal/coordination/YYYY-MM-DD-shortname.pdf` and flip `status` to `published` in `coordination-emails.json` with sender/recipients/subject/passages/attachments filled in. JSON + PDF, no HTML/JS edits.
- Coordination entry status values: `published`, `forthcoming`
- Coordination same-day ordering: JSON array order is presentation order (loader does not re-sort); operator authors the array chronologically and breaks same-day ties by intent
- Bouquet finding categories: `procurement`, `fiduciary`, `process`, `disclosure`, `contractual` — used for grouping, the inline TOC, the category filter, and the muted-hue category badge palette. No bright reds; the page is documentary, not alarmist.
- Bouquet finding status values: `published`, `forthcoming` (forthcoming reserved for placeholder findings; all twelve seeded at launch are `published`)
- `the-bouquet.html` does not use status flips for ongoing publication. Updates land as new `documents` entries appended to existing finding cards (`Update finding <N>: <reason>`) or as new findings appended to the array (`Add finding <N>: <title>`). Findings are not renumbered.
- `the-bouquet.html` asserts no legal conclusions. The page cites statutes, states the record, and lets the reader assess. Phrasing pattern: "Wis. Stat. § X requires Y. The record shows Z." Words deliberately avoided on this page: "embezzlement," "breach," "violation," "misappropriation," "corruption," "fiduciary breach."
