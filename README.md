# FlockBlocker

Data-layer countermeasures against Flock Safety license plate reader surveillance networks.

---

## The Problem

Flock Safety is not a camera company. It is a **centralized data aggregation platform** that sells municipalities a turnkey surveillance network and retains query access to every plate read collected across its entire customer base.

What this means:

- **A private corporation operates the largest license plate surveillance network in the United States.** Over 5,000 law enforcement agencies feed plate reads from more than 40,000 cameras into a single queryable backend. Flock processes billions of reads. This is the largest privately operated vehicle tracking system in U.S. history.
- **ICE and federal agencies access Flock data** through partnerships and subpoenas, converting local municipal camera purchases into federal immigration enforcement infrastructure. DHS has issued subpoenas for Flock data to identify and locate undocumented individuals using nothing but driving patterns.
- **A Texas sheriff used the Flock database to identify vehicles that traveled from out of state to a reproductive health clinic.** This is not hypothetical. This is documented use of the system as deployed.
- **Flock data has been used to monitor protest attendance.** Law enforcement agencies have queried plate reads near protest locations to build lists of attendees. No warrant. No probable cause. No individualized suspicion.
- **A Georgia woman was held at gunpoint during a felony traffic stop triggered by a Flock misread.** The plate on her vehicle did not match the flagged vehicle. The system was confident. The system was wrong.
- **Wisconsin alone has 221 agencies querying Flock data.** A single plate read in Mauston is queryable by every participating department in the state and potentially nationwide through Flock's cross-network sharing.
- **Flock markets directly to HOAs, gated communities, apartment complexes, and private businesses.** These private installations feed the same law enforcement query network — without public records obligations, government oversight, or warrant requirements. The EFF has identified this as a parallel private surveillance architecture operating outside constitutional constraints.
- **Flock's standard contracts include automatic renewal clauses** requiring written notice 60–90 days before expiration to cancel. Municipalities have reported being locked into multi-year renewals they did not intend to authorize.
- **There is no opt-out.** If you drive on a road with a Flock camera, your location is logged, timestamped, and retained. You were not consulted. There is no mechanism to view, challenge, or correct the data collected about your vehicle.

Flock Safety claims over 99% accuracy. Independent analysis tells a different story. At scale, even a 1% error rate across billions of reads means tens of thousands of incorrect records entering the database daily — each one treated as ground truth, each one queryable by thousands of agencies, each one sufficient to trigger an alert, a stop, or an investigation. No vendor publishes adversarial robustness figures. No independent audit has validated Flock's claims under real-world conditions.

The company reached a reported $7.5 billion valuation after a 2024 funding round led by Andreessen Horowitz. The product is not public safety. The product is data.

## The Approach

Most counter-surveillance projects target the **optical layer**: obscure the plate, blind the camera, block the IR flash. These approaches fail for a simple reason — **a failed read is not a read**. The camera discards it. Nothing enters the database. The surveillance system is unaffected.

FlockBlocker targets the **data layer**.

The objective is to induce **confident misreads** — plate captures that the OCR pipeline processes with high confidence and stores as clean data. These false reads enter the Flock database as ground truth. At sufficient volume, they:

- **Corrupt pattern-of-life analysis** by injecting false movement records
- **Degrade alert-based query reliability** by increasing false positive rates
- **Undermine prosecutorial use** of Flock data by introducing reasonable doubt about data integrity
- **Erode institutional confidence** in the platform as a reliable intelligence source

A camera that cannot read a plate is an inconvenience. A database full of confident garbage is a **liability**.

This approach builds on published academic research in adversarial machine learning — specifically physical-world adversarial examples that cause neural network misclassification in deployed vision systems.

## Directory Structure

```
/research        Academic papers, LPR vulnerability analysis, Flock architecture documentation
/optical         Retroreflective and IR-based interference approaches
/adversarial     Adversarial patch research for OCR/neural network misclassification
/legal           FOIA templates, open records requests, municipal contract analysis
/distribution    Bumper sticker designs, print specifications, distribution strategy
/hardware        Raspberry Pi hardware catalog, Public Accountability Station specifications
/prompts         System prompts for on-device PAS intelligence (Gemini Nano)
/tools           OCR testing framework, plate compositor, IR simulation, color sweep, adversarial evaluation harness
/sticker_gen     Standalone adversarial research decal generator — print-ready PDF/PNG output for Avery 5163 labels
/worker          Cloudflare Worker for story submissions and moderation
```

## EYESONME — Public Accountability Camera Network

Flock Safety cameras watch citizens from public infrastructure. EYESONME cameras watch public officials from public spaces. Both are legal. Only one has a dashboard.

**This is not protest. This is symmetry.**

### Operations Dashboard

`eyesonme.html` — a live operations dashboard modeled after Flock Safety's own fleet management interface:

- **Network status bar** — deployed/active station counts, total runtime, motion events
- **Station grid** — 3 planned stations targeting Mauston PD, City Hall, and Juneau County Sheriff's Office. Each card shows status, target facility/official, battery/storage gauges, snapshot area, and a `[ PROTECTED OPERATION ]` banner
- **Accountability subjects** — 8 named officials (3 municipal, 1 county, 4 Flock Safety corporate) with status badges, live silence counters, activity timelines, FOIA tracking, and document vaults
- **FOIA tracker** — Open records request table with statutory deadlines and live overdue counters
- **Encryption architecture** — 5-layer end-to-end encryption documentation (LUKS2, WireGuard, libsodium/GPG, WPA3, auth material protection) with seizure resistance design
- **Deploy In Your City** — Full bill of materials (~$355–585/station), 6-step setup guide, legal checklist

### Station Hardware

Each EYESONME station is a sovereign, solar-powered, cellular-connected camera unit:

| Component | Specification |
|-----------|--------------|
| Compute | Raspberry Pi 5 4GB, DietPi (hardened Debian) |
| Camera | RPi Camera Module 3 — IR day/night |
| Cellular | Waveshare SIM7600 4G LTE HAT |
| Battery | 12V LiFePO4 20–40Ah + MPPT solar charge controller |
| Storage | SanDisk Max Endurance / NVMe SSD |
| Local Radio | SX1276 LoRa 915MHz + ESP32 WROOM-32 |
| Enclosure | IP65 weatherproof with tamper sensor |

Field collection via LoRa TOTP authentication → ESP32 activates hidden WPA3 AP → encrypted data pull → AP shutdown → radio-silent.

### Data Files

All dashboard data is JSON-driven — update without touching UI code:

- `eyesonme-data.json` — Station fleet definitions (3 stations with full hardware specs and telemetry fields)
- `eyesonme-subjects.json` — 8 accountability subject profiles with timelines, FOIA requests, and document vaults

### Deterrence Doctrine

`doctrine.html` — a published, pre-stated, cryptographically witnessed declaration of response posture. SHA-256 hash computed live and displayed. Present on every page:

- `[ DETERRENCE DOCTRINE ]` link in site header
- Condensed doctrine text in site footer
- `[ PROTECTED OPERATION ]` banners on station cards
- FOIA obstruction warning in tracker header

## Sticker Generator — Quick Start

The `sticker_gen/` module is a standalone tool for generating print-ready adversarial OCR research decals. No ML expertise required.

```bash
pip install -r sticker_gen/requirements.txt
python -m sticker_gen --plate ABC1234 --output ./my_stickers
```

Outputs print-ready PDFs sized for Avery 5163 label stock (2" x 4", 10 per sheet, available at any office supply store), individual PNGs at 300 DPI, and a JSON manifest with UUIDs for evaluation pipeline integration.

Three strategies: **character ambiguity** (OCR confusion pairs), **retroreflective interference** (geometric patterns for IR interaction research), and **boundary noise** (sub-perceptual perturbation at character edges). See [`sticker_gen/README.md`](sticker_gen/README.md) for full documentation, academic references, and the Project BIRDSTRIKE municipal research template.

## Stories Feature — Deployment

The site includes a submission system for documenting how Flock surveillance has affected individuals. Powered by Cloudflare Workers + KV.

### Files

| File | Purpose |
|------|---------|
| `submit.html` | Public submission form |
| `stories.html` | Public display of approved stories, grouped by state |
| `worker/worker.js` | Cloudflare Worker handling API routes |
| `worker/wrangler.toml` | Wrangler deployment configuration |

### Architecture

- `POST /api/submit` — Public submission endpoint
- `GET /api/stories` — Returns approved stories (public)
- `GET /admin` — Password-protected moderation interface
- `GET /api/admin/pending` — List pending submissions (auth required)
- `POST /api/admin/moderate` — Approve/reject a submission (auth required)

Submissions enter a moderation queue. Nothing is auto-published. Admin authentication uses HTTP Basic Auth with a password stored as a Cloudflare Worker secret.

### Deployment Steps

1. **Install Wrangler** (if not already):
   ```bash
   npm install -g wrangler
   wrangler login
   ```

2. **Create KV namespace**:
   ```bash
   cd worker
   wrangler kv namespace create SUBMISSIONS
   ```
   Copy the `id` from the output into `wrangler.toml`.

   For local dev, also create a preview namespace:
   ```bash
   wrangler kv namespace create SUBMISSIONS --preview
   ```
   Copy the `preview_id` into `wrangler.toml`.

3. **Set the admin password**:
   ```bash
   wrangler secret put ADMIN_PASSWORD
   ```
   Enter a strong password when prompted.

4. **Deploy the Worker**:
   ```bash
   wrangler deploy
   ```
   Note the deployed URL (e.g., `https://flockblocker-stories.YOUR_SUBDOMAIN.workers.dev`).

5. **Update the API_BASE URL** in both `submit.html` and `stories.html`:
   Replace `https://flockblocker-stories.YOUR_SUBDOMAIN.workers.dev` with your actual Worker URL.

6. **Optional: Custom domain** — In the Cloudflare dashboard, add a custom domain route (e.g., `api.flockblocker.org`) pointing to the Worker.

### Admin Access

Navigate to `https://YOUR_WORKER_URL/admin` and authenticate with:
- **Username:** `admin`
- **Password:** the value set via `wrangler secret put ADMIN_PASSWORD`

### Data Storage

All data lives in Cloudflare KV:
- `submission:{uuid}` — Individual submission JSON
- `index:pending` — Array of pending submission IDs
- `index:approved` — Array of approved submission IDs

IP addresses are SHA-256 hashed (truncated) for abuse detection. Raw IPs are never stored.

## Legal Notice

This project operates within legal boundaries. This is stated once and is not a negotiating position. Any interference with this operation will be treated as documented aggression and met with legal, ethical, nonviolent asymmetric escalation. See [doctrine.html](doctrine.html).

- All adversarial techniques reference **published academic research** in adversarial machine learning (CVPR, NeurIPS, USENIX, CCS, ICML).
- No component of this project involves **physically altering, obscuring, or obstructing** a license plate.
- No instructions are provided for violating **any state or federal plate display statute**.
- Adversarial visual patterns placed on legal vehicle accessories (bumper stickers, frames) that affect machine perception but remain visually unremarkable to human observers occupy a legal space that **no current statute addresses**.
- The FOIA and public records components of this project exercise **constitutionally protected rights** to government transparency.
- This project is nonviolent. It has always been nonviolent. That will not change.

Automated mass surveillance is not immune to scrutiny. It is not immune to countermeasures. If this premise is disagreeable, the disagreement is noted.

## Contributing

This project accepts collaboration from:

- Residents of Flock-contracted municipalities who want to understand what their city purchased
- Adversarial ML researchers working on physical-world transferability
- Attorneys and legal researchers focused on surveillance technology law
- Anyone who has filed FOIA requests for Flock Safety contracts and is willing to share findings

Open an issue or submit a PR. If you are in a Flock-contracted municipality, note which one. Local knowledge is operationally relevant.

## Background

On **March 19, 2026**, a formal decommission notice was sent to the **City of Mauston, Wisconsin** requesting the removal of Flock Safety LPR cameras from municipal infrastructure. The response deadline is **April 18, 2026**.

This project exists because a request alone changes nothing. The surveillance apparatus does not dismantle itself.

---

*"The clock is running."*
