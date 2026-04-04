"""
Core sticker generation engine.

Orchestrates strategy selection, pattern generation, UUID tracking,
and output formatting. Each generated pattern gets a UUID, strategy tag,
and generation parameters stored in JSON for pipeline integration with
the transferability matrix evaluation system.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence

from PIL import Image

from .strategies import STRATEGIES, STRATEGY_DESCRIPTIONS
from .pdf_output import generate_pdf, generate_png, generate_label_sheet_png


def generate_stickers(
    plate_text: str,
    strategy: str = "all",
    output_dir: str = ".",
    variants: int = 1,
    seed: Optional[int] = None,
    output_format: str = "both",
) -> dict:
    """
    Generate adversarial research decals for a given plate text.

    Args:
        plate_text: License plate text to generate patterns for
        strategy: Strategy name or "all" for all strategies
        output_dir: Directory to write output files
        variants: Number of variants per strategy (1-3)
        seed: Random seed for reproducibility
        output_format: "pdf", "png", or "both"

    Returns:
        Generation manifest dict (also saved as JSON)
    """
    plate_text = plate_text.upper().strip()
    variants = max(1, min(3, variants))

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Select strategies
    if strategy == "all":
        selected_strategies = list(STRATEGIES.keys())
    elif strategy in STRATEGIES:
        selected_strategies = [strategy]
    else:
        raise ValueError(
            f"Unknown strategy '{strategy}'. "
            f"Available: {', '.join(STRATEGIES.keys())}, all"
        )

    # Generation manifest for evaluation pipeline integration
    run_id = str(uuid.uuid4())
    manifest = {
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "plate_text": plate_text,
        "seed": seed,
        "tool_version": "1.0.0",
        "stickers": [],
    }

    all_images = []

    for strat_name in selected_strategies:
        gen_func = STRATEGIES[strat_name]

        for v in range(variants):
            sticker_id = str(uuid.uuid4())
            effective_seed = (seed + v) if seed is not None else None

            # Generate the pattern
            img = gen_func(
                plate_text=plate_text,
                seed=effective_seed,
                variant=v,
            )

            # Save individual PNG
            png_name = f"{plate_text}_{strat_name}_v{v}.png"
            png_path = output_path / png_name
            generate_png(img, str(png_path))

            all_images.append(img)

            # Record in manifest
            manifest["stickers"].append({
                "sticker_id": sticker_id,
                "strategy": strat_name,
                "strategy_description": STRATEGY_DESCRIPTIONS[strat_name],
                "variant": v,
                "seed": effective_seed,
                "plate_text": plate_text,
                "output_file": png_name,
                "dimensions": {"width": img.width, "height": img.height},
                "dpi": 300,
                "label_format": "Avery 5163 (2x4 inch)",
            })

    # Generate PDF with all stickers laid out on label sheets
    if output_format in ("pdf", "both"):
        pdf_name = f"{plate_text}_stickers.pdf"
        pdf_path = generate_pdf(
            all_images,
            str(output_path / pdf_name),
            metadata={"strategy": strategy, "plate": plate_text},
        )
        manifest["pdf_output"] = pdf_name

        # Also generate a preview sheet PNG
        preview_name = f"{plate_text}_sheet_preview.png"
        generate_label_sheet_png(all_images, str(output_path / preview_name))
        manifest["preview_output"] = preview_name

    # Save manifest JSON for evaluation pipeline
    manifest_path = output_path / f"{plate_text}_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    manifest["manifest_file"] = str(manifest_path)

    return manifest


def list_strategies() -> dict[str, str]:
    """Return available strategies and their descriptions."""
    return dict(STRATEGY_DESCRIPTIONS)
