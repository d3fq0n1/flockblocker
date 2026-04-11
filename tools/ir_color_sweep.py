"""
IR color-pair contrast optimization sweep.

Systematically searches RGB color space for (background, text) color pairs
that minimize visible-light contrast (invisible to humans) while maximizing
IR contrast (visible to cameras).  Produces ranked tables of optimal pairs
per wavelength for use in IRPhantomConfig.

Usage as script:
    python ir_color_sweep.py                  # default sweep
    python ir_color_sweep.py --wavelength 940 # 940nm only
    python ir_color_sweep.py --top 20         # show top 20 pairs
    python ir_color_sweep.py --json out.json  # export results

The core metric is the **phantom ratio**: IR_contrast / visible_contrast.
Higher ratio = better phantom (invisible to humans, visible to cameras).
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

from ir_simulation import ir_weights_for


# ── Perceptual color distance (CIE76 Delta E in Lab space) ──────────────

def _srgb_to_linear(c: float) -> float:
    """sRGB gamma decode (single channel, 0-1 range)."""
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def _rgb_to_xyz(r: int, g: int, b: int) -> tuple[float, float, float]:
    """Convert sRGB (0-255) to CIE XYZ."""
    rl = _srgb_to_linear(r / 255.0)
    gl = _srgb_to_linear(g / 255.0)
    bl = _srgb_to_linear(b / 255.0)

    x = 0.4124564 * rl + 0.3575761 * gl + 0.1804375 * bl
    y = 0.2126729 * rl + 0.7151522 * gl + 0.0721750 * bl
    z = 0.0193339 * rl + 0.1191920 * gl + 0.9503041 * bl
    return x, y, z


def _xyz_to_lab(x: float, y: float, z: float) -> tuple[float, float, float]:
    """Convert CIE XYZ to CIELAB (D65 illuminant)."""
    # D65 reference white
    xn, yn, zn = 0.95047, 1.00000, 1.08883

    def f(t: float) -> float:
        if t > 0.008856:
            return t ** (1 / 3)
        return 7.787 * t + 16 / 116

    fx = f(x / xn)
    fy = f(y / yn)
    fz = f(z / zn)

    L = 116 * fy - 16
    a = 500 * (fx - fy)
    b_val = 200 * (fy - fz)
    return L, a, b_val


def delta_e(rgb1: tuple[int, int, int], rgb2: tuple[int, int, int]) -> float:
    """CIE76 Delta E between two sRGB colors (perceptual distance)."""
    lab1 = _xyz_to_lab(*_rgb_to_xyz(*rgb1))
    lab2 = _xyz_to_lab(*_rgb_to_xyz(*rgb2))
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(lab1, lab2)))


# ── IR contrast measurement ─────────────────────────────────────────────

def ir_intensity(rgb: tuple[int, int, int], wavelength_nm: int) -> float:
    """Compute the grayscale intensity a color produces under IR simulation."""
    r_w, g_w, b_w = ir_weights_for(wavelength_nm)
    return rgb[0] * r_w + rgb[1] * g_w + rgb[2] * b_w


def ir_contrast(
    bg: tuple[int, int, int],
    fg: tuple[int, int, int],
    wavelength_nm: int,
) -> float:
    """Absolute intensity difference between bg and fg under IR."""
    return abs(ir_intensity(bg, wavelength_nm) - ir_intensity(fg, wavelength_nm))


# ── Sweep result ─────────────────────────────────────────────────────────

@dataclass
class ColorPairResult:
    """Evaluation result for a single (bg, fg) color pair."""
    bg_rgb: tuple[int, int, int]
    fg_rgb: tuple[int, int, int]
    wavelength_nm: int
    visible_delta_e: float
    ir_contrast: float

    @property
    def phantom_ratio(self) -> float:
        """IR contrast / visible contrast.  Higher = better phantom."""
        if self.visible_delta_e < 0.01:
            return self.ir_contrast * 100  # near-zero visible = excellent
        return self.ir_contrast / self.visible_delta_e


@dataclass
class SweepResult:
    """Full sweep output for one wavelength."""
    wavelength_nm: int
    pairs: list[ColorPairResult] = field(default_factory=list)
    sample_count: int = 0

    @property
    def top(self) -> list[ColorPairResult]:
        return sorted(self.pairs, key=lambda p: p.phantom_ratio, reverse=True)

    def summary(self, n: int = 10) -> list[dict]:
        return [
            {
                "rank": i + 1,
                "bg_rgb": p.bg_rgb,
                "fg_rgb": p.fg_rgb,
                "visible_delta_e": round(p.visible_delta_e, 2),
                "ir_contrast": round(p.ir_contrast, 2),
                "phantom_ratio": round(p.phantom_ratio, 2),
            }
            for i, p in enumerate(self.top[:n])
        ]


# ── Sweep engine ─────────────────────────────────────────────────────────

def _generate_candidates(
    step: int = 20,
    min_val: int = 0,
    max_val: int = 255,
) -> list[tuple[int, int, int]]:
    """Generate candidate RGB colors at regular intervals."""
    values = list(range(min_val, max_val + 1, step))
    return list(itertools.product(values, values, values))


def sweep(
    wavelength_nm: int = 850,
    max_visible_delta_e: float = 15.0,
    min_ir_contrast: float = 5.0,
    step: int = 20,
) -> SweepResult:
    """
    Search color space for optimal phantom color pairs.

    Args:
        wavelength_nm: Target IR wavelength.
        max_visible_delta_e: Maximum perceptual difference allowed in visible
            light.  Lower = harder to see.  Delta E < 1 is imperceptible;
            < 5 is noticeable only under close inspection; < 15 is "similar".
        min_ir_contrast: Minimum grayscale intensity difference required
            under IR.  Higher = more visible to the camera.
        step: RGB sampling step size.  Smaller = finer search, slower.
            20 gives ~2K candidates (~2M pairs); 10 gives ~18K candidates.

    Returns:
        SweepResult with all qualifying pairs, ranked by phantom_ratio.
    """
    candidates = _generate_candidates(step=step)
    result = SweepResult(wavelength_nm=wavelength_nm)

    # Pre-compute IR intensities for all candidates
    ir_cache: dict[tuple[int, int, int], float] = {}
    for c in candidates:
        ir_cache[c] = ir_intensity(c, wavelength_nm)

    n_candidates = len(candidates)
    result.sample_count = n_candidates * (n_candidates - 1) // 2

    for i in range(n_candidates):
        bg = candidates[i]
        bg_ir = ir_cache[bg]

        for j in range(i + 1, n_candidates):
            fg = candidates[j]
            fg_ir = ir_cache[fg]

            # Fast IR contrast check first (cheap)
            ir_diff = abs(bg_ir - fg_ir)
            if ir_diff < min_ir_contrast:
                continue

            # Expensive perceptual distance check only if IR passes
            de = delta_e(bg, fg)
            if de > max_visible_delta_e:
                continue

            result.pairs.append(ColorPairResult(
                bg_rgb=bg,
                fg_rgb=fg,
                wavelength_nm=wavelength_nm,
                visible_delta_e=de,
                ir_contrast=ir_diff,
            ))

    return result


def sweep_all_wavelengths(
    wavelengths: Sequence[int] = (850, 940),
    **kwargs,
) -> dict[int, SweepResult]:
    """Run sweep for each wavelength and return combined results."""
    return {wl: sweep(wavelength_nm=wl, **kwargs) for wl in wavelengths}


# ── Display ──────────────────────────────────────────────────────────────

def format_results(result: SweepResult, n: int = 10) -> str:
    """Format sweep results as an ASCII table."""
    top = result.top[:n]
    if not top:
        return f"No qualifying pairs found for {result.wavelength_nm}nm"

    lines = [
        "",
        f"{'=' * 78}",
        f"TOP {n} PHANTOM COLOR PAIRS @ {result.wavelength_nm}nm",
        f"({result.sample_count:,} pairs evaluated, "
        f"{len(result.pairs):,} qualifying)",
        f"{'=' * 78}",
        f"{'Rank':<5} {'Background':<18} {'Foreground':<18} "
        f"{'Vis dE':<9} {'IR Δ':<9} {'Ratio':<9}",
        f"{'-' * 78}",
    ]

    for i, p in enumerate(top, 1):
        lines.append(
            f"{i:<5} {str(p.bg_rgb):<18} {str(p.fg_rgb):<18} "
            f"{p.visible_delta_e:<9.2f} {p.ir_contrast:<9.1f} "
            f"{p.phantom_ratio:<9.1f}"
        )

    lines.append(f"{'=' * 78}")
    return "\n".join(lines)


# ── CLI ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Find optimal IR phantom color pairs."
    )
    parser.add_argument(
        "--wavelength", type=int, default=None,
        help="Single wavelength to sweep (default: both 850 and 940)",
    )
    parser.add_argument(
        "--max-delta-e", type=float, default=15.0,
        help="Max visible-light perceptual distance (default: 15.0)",
    )
    parser.add_argument(
        "--min-ir-contrast", type=float, default=5.0,
        help="Min IR grayscale contrast (default: 5.0)",
    )
    parser.add_argument(
        "--step", type=int, default=20,
        help="RGB sampling step size (default: 20)",
    )
    parser.add_argument(
        "--top", type=int, default=10,
        help="Number of top results to show (default: 10)",
    )
    parser.add_argument(
        "--json", type=str, default=None,
        help="Export results to JSON file",
    )

    args = parser.parse_args()

    wavelengths = [args.wavelength] if args.wavelength else [850, 940]

    all_results = {}
    for wl in wavelengths:
        print(f"Sweeping {wl}nm (step={args.step}) ...")
        result = sweep(
            wavelength_nm=wl,
            max_visible_delta_e=args.max_delta_e,
            min_ir_contrast=args.min_ir_contrast,
            step=args.step,
        )
        all_results[wl] = result
        print(format_results(result, n=args.top))

    if args.json:
        export = {
            str(wl): result.summary(n=args.top)
            for wl, result in all_results.items()
        }
        with open(args.json, "w") as f:
            json.dump(export, f, indent=2)
        print(f"\nResults exported to {args.json}")


if __name__ == "__main__":
    main()
