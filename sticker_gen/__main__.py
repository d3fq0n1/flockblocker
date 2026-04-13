#!/usr/bin/env python3
"""
FlockBlocker Sticker Generator — CLI Entry Point

Generate print-ready adversarial OCR research decals.

Usage:
    python -m sticker_gen --plate ABC1234
    python -m sticker_gen --plate ABC1234 --strategy character_ambiguity --output ./output
    python -m sticker_gen --plate ABC1234 --strategy all --variants 3 --format pdf

For more information: https://flockblocker.org/birdstrike.html
"""

import argparse
import sys

from .generator import generate_stickers, list_strategies


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="sticker_gen",
        description=(
            "FlockBlocker Adversarial OCR Research Decal Generator. "
            "Generates print-ready research decals documenting ALPR system "
            "vulnerabilities. Academic research use."
        ),
        epilog=(
            "For research context and legal framework, see: "
            "https://flockblocker.org/birdstrike.html"
        ),
    )

    parser.add_argument(
        "--plate",
        required=True,
        help="Target plate text (e.g., ABC1234)",
    )
    parser.add_argument(
        "--strategy",
        default="all",
        choices=["all", "character_ambiguity", "retroreflective", "boundary_noise"],
        help=(
            "Pattern generation strategy (default: all). "
            "sticker_gen is the print-ready-sticker subset of the canonical "
            "six strategies in CLAUDE.md. The research-only strategies "
            "(ir_phantom, eot_adversarial, ensemble_eot) live in "
            "tools/decal_generator.py + tools/ensemble_eot.py — they "
            "require IR camera simulation or gradient optimization and "
            "are not usefully expressible as a printed bumper sticker."
        ),
    )
    parser.add_argument(
        "--output",
        default="./sticker_output",
        help="Output directory (default: ./sticker_output)",
    )
    parser.add_argument(
        "--variants",
        type=int,
        default=1,
        choices=[1, 2, 3],
        help="Number of variants per strategy (default: 1)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        default="both",
        choices=["pdf", "png", "both"],
        help="Output format (default: both)",
    )
    parser.add_argument(
        "--list-strategies",
        action="store_true",
        help="List available strategies and exit",
    )

    args = parser.parse_args()

    if args.list_strategies:
        print("\nAvailable strategies:\n")
        for name, desc in list_strategies().items():
            print(f"  {name:25s} {desc}")
        print(
            "\nUse --strategy <name> to select one, or --strategy all for all.\n"
        )
        return 0

    print(f"FlockBlocker Sticker Generator v1.0.0")
    print(f"Generating research decals for plate: {args.plate}")
    print(f"Strategy: {args.strategy}")
    print(f"Output: {args.output}")
    print()

    try:
        manifest = generate_stickers(
            plate_text=args.plate,
            strategy=args.strategy,
            output_dir=args.output,
            variants=args.variants,
            seed=args.seed,
            output_format=args.output_format,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Summary
    print(f"Generated {len(manifest['stickers'])} sticker(s):")
    for s in manifest["stickers"]:
        print(f"  [{s['strategy']}] v{s['variant']} -> {s['output_file']}")

    if "pdf_output" in manifest:
        print(f"\nPrint-ready PDF: {manifest['pdf_output']}")
    if "preview_output" in manifest:
        print(f"Sheet preview:   {manifest['preview_output']}")

    print(f"\nManifest: {manifest['manifest_file']}")
    print(f"Run ID:   {manifest['run_id']}")
    print(
        "\n--- Academic research use. Not for vehicle code interference. ---"
    )
    print("https://flockblocker.org/birdstrike.html\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
