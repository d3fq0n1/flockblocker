# FlockBlocker Sticker Generator

**Adversarial OCR Research Decal Tool**

A standalone tool for generating print-ready adversarial research decals that document vulnerabilities in Automated License Plate Recognition (ALPR) optical character recognition pipelines. Part of the [FlockBlocker](https://flockblocker.org/birdstrike.html) civic research initiative and the **Project BIRDSTRIKE** replicable research template.

---

## What This Tool Does

This tool generates printable sticker patterns that exploit documented weaknesses in OCR (Optical Character Recognition) systems used by ALPR cameras. It implements three peer-reviewed adversarial strategies:

1. **Character Ambiguity** — Exploits known OCR confusion pairs (0/O, 1/I/l, 8/B, 5/S, 2/Z) using font-weight and stroke-width manipulation at the boundary of human legibility vs. machine classification confidence. Output is human-readable. Machine confidence degrades.

2. **Retroreflective Interference** — Generates high-contrast geometric patterns calibrated for retroreflective substrate interaction. Documents how pattern placement affects OCR confidence scoring. Patterns are decorative in the visible spectrum; the research documents IR-band interaction.

3. **Boundary Noise** — Fine-grain noise patterns along character boundary regions, below human perceptual threshold but within documented OCR confidence degradation ranges from published literature.

Each generated output includes a UUID, strategy metadata, and a JSON manifest for integration with FlockBlocker's evaluation framework and transferability matrix.

## What This Tool Does NOT Do

- **Does not physically damage or tamper with any camera hardware**
- **Does not access, hack, or interfere with any computer system**
- **Does not advocate placing materials on vehicle plates in jurisdictions where doing so violates vehicle codes** — check your local laws before any physical-world application
- **Does not interfere with active law enforcement operations**
- **Does not produce any output that cannot be generated with a standard label printer and off-the-shelf label stock**

This is academic adversarial ML research made accessible to civilians, in the same tradition as the EFF's [Surveillance Self-Defense](https://ssd.eff.org/) project.

---

## Quickstart

```bash
# Clone the repo
git clone https://github.com/d3fq0n1/flockblocker.git
cd flockblocker

# Install dependencies (minimal: Pillow, reportlab, numpy)
pip install -r sticker_gen/requirements.txt

# Generate research decals for a plate — that's it
python -m sticker_gen --plate ABC1234 --output ./my_stickers
```

Output (under 2 minutes on any machine):
- Individual PNG sticker images (300 DPI, print-ready)
- Print-ready PDF laid out for **Avery 5163** label stock (2" x 4", 10 per sheet)
- Sheet preview PNG
- JSON manifest with UUIDs and generation parameters for evaluation pipeline

### More Examples

```bash
# Single strategy
python -m sticker_gen --plate HBR4051 --strategy character_ambiguity

# All strategies with 3 variants each (9 total stickers)
python -m sticker_gen --plate WKM7793 --strategy all --variants 3

# PNG only, reproducible seed
python -m sticker_gen --plate ABC1234 --format png --seed 42

# List available strategies
python -m sticker_gen --plate X --list-strategies
```

---

## Output Format

### Label Specifications
- **Label stock:** Avery 5163 or equivalent (available at Walmart, Staples, Amazon)
- **Label size:** 2" x 4" (10 per sheet on US Letter)
- **Resolution:** 300 DPI
- **Printer:** Standard laser or inkjet. No specialty materials required.

### Research Attribution
Every generated output includes:
- Embedded PDF metadata with project attribution
- Visible footer: *"FlockBlocker Adversarial OCR Research — flockblocker.org/birdstrike.html — Academic research use. Not for vehicle code interference."*
- JSON manifest with full generation parameters, UUIDs, and strategy tags

---

## Evaluation Integration

Generated stickers integrate with FlockBlocker's evaluation framework. The JSON manifest produced by each run contains:

```json
{
  "run_id": "uuid-v4",
  "generated_at": "ISO-8601 timestamp",
  "plate_text": "ABC1234",
  "stickers": [
    {
      "sticker_id": "uuid-v4",
      "strategy": "character_ambiguity",
      "variant": 0,
      "seed": 42,
      "output_file": "ABC1234_character_ambiguity_v0.png"
    }
  ]
}
```

Feed generated PNGs into the evaluation pipeline:

```python
from tools.evaluation import evaluate_decal

score = evaluate_decal(
    decal_image_path="sticker_output/ABC1234_character_ambiguity_v0.png",
    plate_texts=["ABC1234"],
    decal_name="ABC1234_character_ambiguity_v0",
    strategy="character_ambiguity",
)
print(f"Misread rate: {score.misread_rate:.1%}")
print(f"Transferability: {score.transferability:.1%}")
```

---

## Dependencies

Core (required):
- `Pillow>=10.0.0` — Image generation
- `reportlab>=4.0.0` — PDF output
- `numpy>=1.24.0` — Numerical operations

Optional:
- `torch>=2.1.0` — EOT adversarial patch strategy only (not required for the three core strategies)

Install: `pip install -r sticker_gen/requirements.txt`

---

## How to Use This in Your Municipality

This tool is the technical arm of **Project BIRDSTRIKE** — a replicable civic research template for any Flock Safety-contracted municipality.

### For Residents

1. **Check if your municipality contracts with Flock Safety.** Over 5,000 municipalities do, including Mt. Juliet TN, Mauston WI, and thousands of others. Check your city council minutes or police department contracts.

2. **Clone this repo and generate research artifacts:**
   ```bash
   git clone https://github.com/d3fq0n1/flockblocker.git
   cd flockblocker
   pip install -r sticker_gen/requirements.txt
   python -m sticker_gen --plate ABC1234 --output ./research_output
   ```

3. **Document your research.** The JSON manifests provide a complete audit trail of what was generated, when, how, and why.

4. **Engage your local government.** Use the BIRDSTRIKE template at [flockblocker.org/birdstrike.html](https://flockblocker.org/birdstrike.html) for:
   - Public records requests for Flock Safety contracts
   - City council public comment frameworks
   - Research presentation templates
   - Legal and ethical research framework documentation

5. **Contribute to the empirical dataset.** Run the evaluation pipeline against your generated patterns and submit results to build the community transferability matrix.

### For Civic Technologists

The evaluation framework in `tools/evaluation.py` provides:
- Cross-engine transferability matrix (NxN pairwise transfer rates)
- Per-strategy effectiveness breakdowns
- Composite scoring (misread rate + confidence + transferability)
- JSON export for aggregation across research sites

### For Researchers

This tool implements methodologies from:
- Eykholt et al., "Robust Physical-World Attacks on Deep Learning Models" (CVPR 2018)
- Song et al., "Fooling OCR Systems with Adversarial Text Images" (2022)
- TPAMI 2022 Adversarial Sticker methodology
- Athalye et al., "Synthesizing Robust Adversarial Examples" (ICML 2018) — EOT framework

The transferability matrix framework follows standard adversarial ML evaluation practices as published in IEEE, USENIX, and CVPR proceedings.

---

## Legal and Ethical Framework

This project is **academic adversarial ML research**. It operates within the same legal and ethical framework as:

- **EFF's Surveillance Self-Defense** — civilian education about surveillance technology
- **USENIX Security / IEEE S&P** — peer-reviewed adversarial ML research
- **CVPR adversarial examples literature** — physical-world adversarial perturbation research

### What This Research Demonstrates

ALPR systems have **architectural vulnerabilities** in their OCR pipelines. These vulnerabilities are:
- **Documented in peer-reviewed literature**
- **Reproducible with consumer-grade materials**
- **Relevant to public policy decisions** about surveillance infrastructure procurement

### What This Research Is NOT

- Not vandalism — no property is damaged
- Not hacking — no computer systems are accessed
- Not obstruction — research artifacts are documented, attributed, and traceable
- Not vehicle code violation advocacy — **always check your local laws before any physical-world application of research findings**

### First Amendment Considerations

Research, documentation, and publication of system vulnerabilities is protected expression. This project publishes findings, not exploits. The distinction is the same one recognized by every major security conference, the EFF, and the DMCA security research exemption (17 U.S.C. 1201(j)).

---

## Project Structure

```
sticker_gen/
├── __init__.py          # Package metadata, research footer constant
├── __main__.py          # CLI entry point
├── generator.py         # Core generation orchestrator, UUID tracking, manifest
├── strategies.py        # Three adversarial pattern strategies
├── pdf_output.py        # PDF/PNG output for Avery 5163 label stock
├── requirements.txt     # Minimal pinned dependencies
└── README.md            # This file
```

---

## Links

- **Project BIRDSTRIKE:** [flockblocker.org/birdstrike.html](https://flockblocker.org/birdstrike.html)
- **Repository:** [github.com/d3fq0n1/flockblocker](https://github.com/d3fq0n1/flockblocker)
- **EFF Surveillance Self-Defense:** [ssd.eff.org](https://ssd.eff.org/)
- **Flock Safety municipal contract database:** See BIRDSTRIKE template for FOIA/public records request frameworks

---

*FlockBlocker Adversarial OCR Research — Academic research use. Not for vehicle code interference.*
