#!/usr/bin/env python3
"""
Generate decal fixture images for the test suite.

Run this to populate tools/fixtures/decals/ with decal candidates
that the test_decal_effect.py tests can use.

Usage:
    python generate_fixtures.py [--target-plate ABC1234] [--variants 3]
"""

import argparse
import sys
from pathlib import Path

# Ensure tools/ is importable
sys.path.insert(0, str(Path(__file__).parent))

from decal_generator import generate_candidate_suite


def main():
    parser = argparse.ArgumentParser(description="Generate decal test fixtures")
    parser.add_argument(
        "--target-plate",
        default=None,
        help="Generate targeted decals for this plate text",
    )
    parser.add_argument(
        "--variants",
        type=int,
        default=3,
        help="Number of variants per strategy (default: 3)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory (default: tools/fixtures/decals)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility",
    )
    args = parser.parse_args()

    output_dir = args.output_dir or str(
        Path(__file__).parent / "fixtures" / "decals"
    )

    print(f"Generating decal fixtures to: {output_dir}")
    print(f"  Target plate: {args.target_plate or '(untargeted)'}")
    print(f"  Variants per strategy: {args.variants}")
    print(f"  Seed: {args.seed}")
    print()

    candidates = generate_candidate_suite(
        target_plate=args.target_plate,
        output_dir=output_dir,
        variants_per_strategy=args.variants,
        seed=args.seed,
    )

    print(f"Generated {len(candidates)} decal candidates:")
    for c in candidates:
        print(f"  [{c.strategy}] {Path(c.path).name}")

    print(f"\nFixtures written to: {output_dir}")
    print("Run tests with: cd tools && python -m pytest tests/ -v")


if __name__ == "__main__":
    main()
