# /legal/coordination

Email PDF exhibits cited from `the-coordination.html`, sourced from City of Mauston open records productions.

## Filename convention

```
YYYY-MM-DD-shortname.pdf
```

- `YYYY-MM-DD` — date the email was sent.
- `shortname` — lowercase, hyphenated, identifies the email at a glance (sender surname + topic, e.g. `gautam-talking-points`, `tajik-foia-guidance`).

The full path used in `coordination-emails.json` (`source.pdf_path`) is `legal/coordination/<filename>`.

Example: `legal/coordination/2026-04-09-gautam-talking-points.pdf`.

## Operator drop-in workflow

To publish a forthcoming entry that the page already lists as `status: "forthcoming"`:

1. Place the email PDF in this directory using the naming convention above.
2. Open `coordination-emails.json` at repo root.
3. Find the entry by `id`.
4. Change `status` from `forthcoming` to `published`.
5. Fill in `sender`, `recipients`, `subject`, `time`, `passages`, `attachments`, and `source` (including `pdf_path` matching the file you just placed).
6. Commit with message: `Publish coordination entry: <id>`.
7. Push.

The page renders the new entry on next page load. No HTML edits, no JS edits.

## Production cover letters

Production cover letters (the City Administrator's transmittal letters that accompany each open records release) are listed in `coordination-productions.json` and may live at paths such as `legal/coordination/2026-04-23-cover-letter.pdf`. Same naming convention.
