# /legal/bouquet

Exhibit PDFs cited from `the-bouquet.html`. Sourced from the City of Mauston's open records productions and from the public probate record of the Estate of Glenn T. Buehlman (Juneau County Case No. 2022PR000027).

## Filename convention

```
YYYY-MM-DD-shortname.pdf
```

- `YYYY-MM-DD` — date of the document.
- `shortname` — lowercase, hyphenated.

The full path used in `bouquet-findings.json` (`documents[].path`) is `legal/bouquet/<filename>`.

## Documents the operator still needs to drop in

These are referenced by the seeded findings with `path` markers under `legal/bouquet/`. Until the operator places them, the rendered page shows "pending placement" next to the link.

| Finding | Document | Suggested filename |
|---------|----------|--------------------|
| 1, 3, 9, 10, 11 | City Administrator response, April 27, 2026 | `2026-04-27-haugh-response.pdf` |
| 2 | Withdrawal slip — $10,000 from K9 CD, March 13, 2024 (signed Haugh + Zilisch) | `2024-03-13-k9-cd-withdrawal-slip.pdf` |
| 2 | Bank of Mauston transaction screenshots | `2024-03-13-bom-transaction-screenshots.pdf` |
| 2 | Buehlman estate accounting — Schedule M | `2022PR000027-schedule-m.pdf` |
| 2 | Buehlman estate accounting — Schedule O | `2022PR000027-schedule-o.pdf` |
| 2 | Schedule K-1 (Form 1041), tax year 2022 | `2022PR000027-k1-form-1041.pdf` |
| 2 | Curran Law Office cover letter, July 5, 2023 | `2023-07-05-curran-cover-letter.pdf` |
| 2 | Estate Receipt PR-1815, July 10, 2023 | `2023-07-10-estate-receipt-pr-1815.pdf` |
| 4 | April 7, 2026 wrong-document production (unsigned $50,200 quote) | `2026-04-07-zilisch-wrong-document.pdf` |
| 5 | Zilisch email of April 22, 2022 | `2022-04-22-zilisch-data-sharing.pdf` |
| 5 | Flock data-sharing agreement (if produced) | `2022-04-22-flock-data-sharing-agreement.pdf` |
| 8 | Gautam Ratnam talking-points email, April 9, 2026 | shared with `legal/coordination/2026-04-09-gautam-talking-points.pdf` |
| 9 | Operator's supplemental records request, April 23, 2026 | `2026-04-23-supplemental-request.pdf` |

Documents already present at repo root and referenced as-is from JSON:

- `Flock Executed Agreement - Signed.pdf` — Findings 1, 6, 7, 12
- `Response to Clark, Blake.pdf` — Finding 1 (city response, April 20, 2026)

Documents already present in `flockdocs/` (cherry-picked onto this branch from the upload branch) and referenced from JSON:

- `flockdocs/JE-24-015.pdf` — Finding 2 (journal entry reclassifying K9 funds)
- `flockdocs/JE-24-016.pdf` — Finding 3 (Bank Account Interest JE, March 2024)

## Drop-in workflow

1. Place the PDF in this directory using the naming convention above (or wherever the JSON references it; the JSON's `path` field is authoritative).
2. Confirm `bouquet-findings.json` already references it via `path`. If not, add or update the document entry.
3. Commit with message: `Add bouquet exhibit: <shortname>`.
4. Push.

The page renders the link on next page load. No HTML edits, no JS edits.

## Provenance note

Every exhibit on this page is sourced to either a City of Mauston open records production (April 20, April 23, or April 27, 2026 — see `bouquet-sources.json`) or to the public probate record. A reader who wants to verify a finding can trace it from the finding card → document → source production → underlying records request or court filing.
