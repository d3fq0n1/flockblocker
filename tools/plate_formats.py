"""
US license plate format rules for all 50 states + DC.

Provides structured format definitions that enable:
1. **Generation** — produce realistic plate strings for any state
2. **Validation** — check if a string is a plausible plate for a given state
3. **Constraint** — ensure adversarial misreads produce plausible plates

Each state entry defines one or more ``PlatePattern`` objects describing the
standard passenger vehicle plate format.  Specialty, vanity, commercial, and
temporary plates are out of scope — standard passenger covers ~80% of
real-world encounters.

Format data sourced from publicly available DMV documentation and plate
collector references.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Sequence


# ── Segment types ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Segment:
    """One segment of a plate format (e.g., 3 alpha chars)."""
    type: str       # "alpha", "digit", "alphanumeric"
    length: int     # number of characters in this segment

    @property
    def charset(self) -> str:
        if self.type == "alpha":
            return "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        elif self.type == "digit":
            return "0123456789"
        else:  # alphanumeric
            return "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

    @property
    def regex(self) -> str:
        if self.type == "alpha":
            return f"[A-Z]{{{self.length}}}"
        elif self.type == "digit":
            return f"[0-9]{{{self.length}}}"
        else:
            return f"[A-Z0-9]{{{self.length}}}"


@dataclass(frozen=True)
class PlatePattern:
    """A complete plate format pattern.

    A plate like "ABC-1234" is represented as:
        segments=[Segment("alpha", 3), Segment("digit", 4)]
        separator="-"
    The separator appears between segments but is stripped for OCR comparison.
    """
    segments: tuple[Segment, ...]
    separator: str = ""         # character between segments (visual only)
    description: str = ""       # human-readable label

    @property
    def total_length(self) -> int:
        return sum(s.length for s in self.segments)

    @property
    def regex(self) -> str:
        """Regex matching the raw plate string (no separators)."""
        return "^" + "".join(s.regex for s in self.segments) + "$"

    def validate(self, text: str) -> bool:
        """Check if text matches this plate pattern (separator-stripped)."""
        clean = text.upper().replace(" ", "").replace("-", "").replace("·", "")
        return bool(re.match(self.regex, clean))

    def generate(self, rng: random.Random | None = None) -> str:
        """Generate a random plate string matching this pattern."""
        r = rng or random.Random()
        parts = []
        for seg in self.segments:
            parts.append("".join(r.choice(seg.charset) for _ in range(seg.length)))
        return "".join(parts)

    def generate_with_separator(self, rng: random.Random | None = None) -> str:
        """Generate with visual separator (e.g., 'ABC-1234')."""
        r = rng or random.Random()
        parts = []
        for seg in self.segments:
            parts.append("".join(r.choice(seg.charset) for _ in range(seg.length)))
        return self.separator.join(parts)


# ── Convenience constructors ───────────────────────────────────────────────

def _p(fmt_str: str, sep: str = "", desc: str = "") -> PlatePattern:
    """Build a PlatePattern from a compact format string.

    Format codes:
        A = 1 alpha char
        9 = 1 digit
        X = 1 alphanumeric

    Example: "AAA9999" → 3 alpha + 4 digit
             "9AAA999" → 1 digit + 3 alpha + 3 digit
    """
    segments: list[Segment] = []
    i = 0
    while i < len(fmt_str):
        ch = fmt_str[i]
        if ch == " ":
            i += 1
            continue  # spaces in format string are visual separators, skip
        seg_type = {"A": "alpha", "9": "digit", "X": "alphanumeric"}[ch]
        length = 1
        while i + length < len(fmt_str) and fmt_str[i + length] == ch:
            length += 1
        segments.append(Segment(seg_type, length))
        i += length
    return PlatePattern(tuple(segments), separator=sep, description=desc)


# ═══════════════════════════════════════════════════════════════════════════
# All 50 states + DC — standard passenger plate formats
# ═══════════════════════════════════════════════════════════════════════════
#
# Many states have multiple valid formats (new vs. legacy, county variations).
# We list the most common current-issue format first, plus significant
# alternates.  Data current as of 2025.

STATE_FORMATS: dict[str, list[PlatePattern]] = {
    "AL": [
        _p("99AA999", desc="Alabama: digit digit alpha alpha digit digit digit"),
        _p("AA99AA9", desc="Alabama alt"),
    ],
    "AK": [
        _p("AAA999", desc="Alaska: 3 alpha + 3 digit"),
    ],
    "AZ": [
        _p("AAA9999", desc="Arizona: 3 alpha + 4 digit"),
        _p("999AAAA", desc="Arizona alt: 3 digit + 4 alpha"),
    ],
    "AR": [
        _p("999AAA", desc="Arkansas: 3 digit + 3 alpha"),
        _p("AAA99A", desc="Arkansas alt"),
    ],
    "CA": [
        _p("9AAA999", desc="California: 1 digit + 3 alpha + 3 digit"),
    ],
    "CO": [
        _p("AAA999", desc="Colorado: 3 alpha + 3 digit"),
        _p("999AAA", desc="Colorado alt"),
        _p("AAAA99", desc="Colorado 4+2"),
    ],
    "CT": [
        _p("AA99999", desc="Connecticut: 2 alpha + 5 digit"),
        _p("999AAA", desc="Connecticut alt"),
    ],
    "DE": [
        _p("999999", desc="Delaware: 6 digit"),
        _p("99999", desc="Delaware 5-digit"),
    ],
    "DC": [
        _p("AA9999", desc="DC: 2 alpha + 4 digit"),
    ],
    "FL": [
        _p("AAAA99", desc="Florida: 4 alpha + 2 digit"),
        _p("AAA999", desc="Florida: 3 alpha + 3 digit"),
        _p("999AAA", desc="Florida alt"),
    ],
    "GA": [
        _p("AAA9999", desc="Georgia: 3 alpha + 4 digit"),
        _p("AAA999", desc="Georgia 3+3"),
    ],
    "HI": [
        _p("AAA999", desc="Hawaii: 3 alpha + 3 digit"),
        _p("AAAA99", desc="Hawaii 4+2"),
    ],
    "ID": [
        _p("9A99999", desc="Idaho: county digit + alpha + 5 digit"),
        _p("AA99999", desc="Idaho alt"),
    ],
    "IL": [
        _p("AA99999", desc="Illinois: 2 alpha + 5 digit"),
        _p("999999", desc="Illinois 6-digit"),
    ],
    "IN": [
        _p("999AAA", desc="Indiana: 3 digit + 3 alpha"),
    ],
    "IA": [
        _p("AAA999", desc="Iowa: 3 alpha + 3 digit"),
        _p("999AAA", desc="Iowa alt"),
    ],
    "KS": [
        _p("999AAA", desc="Kansas: 3 digit + 3 alpha"),
    ],
    "KY": [
        _p("999AAA", desc="Kentucky: 3 digit + 3 alpha"),
    ],
    "LA": [
        _p("999AAA", desc="Louisiana: 3 digit + 3 alpha"),
    ],
    "ME": [
        _p("9999AA", desc="Maine: 4 digit + 2 alpha"),
    ],
    "MD": [
        _p("9AA9999", desc="Maryland: 1 digit + 2 alpha + 4 digit"),
    ],
    "MA": [
        _p("9AAA99", desc="Massachusetts: 1 digit + 3 alpha + 2 digit"),
        _p("99AA99", desc="Massachusetts alt"),
    ],
    "MI": [
        _p("AAA9999", desc="Michigan: 3 alpha + 4 digit"),
        _p("9AAA99", desc="Michigan alt"),
    ],
    "MN": [
        _p("999AAA", desc="Minnesota: 3 digit + 3 alpha"),
    ],
    "MS": [
        _p("AAA9999", desc="Mississippi: 3 alpha + 4 digit"),
        _p("AAA999", desc="Mississippi 3+3"),
    ],
    "MO": [
        _p("AA9A9A", desc="Missouri: 2 alpha + digit + alpha + digit + alpha"),
        _p("999AAA", desc="Missouri alt"),
    ],
    "MT": [
        _p("99A9999", desc="Montana: county digits + alpha + 4 digit"),
        _p("999999A", desc="Montana alt"),
    ],
    "NE": [
        _p("AAA999", desc="Nebraska: 3 alpha + 3 digit"),
        _p("9AA999", desc="Nebraska alt"),
    ],
    "NV": [
        _p("999A999", desc="Nevada: 3 digit + alpha + 3 digit"),
    ],
    "NH": [
        _p("999999", desc="New Hampshire: 6 digit"),
        _p("9999999", desc="New Hampshire 7-digit"),
    ],
    "NJ": [
        _p("A99AAA", desc="New Jersey: alpha + 2 digit + 3 alpha"),
        _p("AAA99A", desc="New Jersey alt"),
    ],
    "NM": [
        _p("999AAA", desc="New Mexico: 3 digit + 3 alpha"),
        _p("AAAA99", desc="New Mexico 4+2"),
    ],
    "NY": [
        _p("AAA9999", desc="New York: 3 alpha + 4 digit"),
    ],
    "NC": [
        _p("AAA9999", desc="North Carolina: 3 alpha + 4 digit"),
    ],
    "ND": [
        _p("999AAA", desc="North Dakota: 3 digit + 3 alpha"),
    ],
    "OH": [
        _p("AAA9999", desc="Ohio: 3 alpha + 4 digit"),
    ],
    "OK": [
        _p("AAA999", desc="Oklahoma: 3 alpha + 3 digit"),
    ],
    "OR": [
        _p("999AAA", desc="Oregon: 3 digit + 3 alpha"),
    ],
    "PA": [
        _p("AAA9999", desc="Pennsylvania: 3 alpha + 4 digit"),
    ],
    "RI": [
        _p("AA999", desc="Rhode Island: 2 alpha + 3 digit"),
        _p("999999", desc="Rhode Island 6-digit"),
    ],
    "SC": [
        _p("AAA999", desc="South Carolina: 3 alpha + 3 digit"),
        _p("999AAA", desc="South Carolina alt"),
    ],
    "SD": [
        _p("9AA999", desc="South Dakota: county digit + 2 alpha + 3 digit"),
        _p("99A999", desc="South Dakota alt"),
    ],
    "TN": [
        _p("999AAA", desc="Tennessee: 3 digit + 3 alpha"),
    ],
    "TX": [
        _p("AAA9999", desc="Texas: 3 alpha + 4 digit"),
    ],
    "UT": [
        _p("A999AA", desc="Utah: alpha + 3 digit + 2 alpha"),
        _p("AA9999", desc="Utah alt"),
    ],
    "VT": [
        _p("AAA999", desc="Vermont: 3 alpha + 3 digit"),
        _p("999999", desc="Vermont numeric"),
    ],
    "VA": [
        _p("AAA9999", desc="Virginia: 3 alpha + 4 digit"),
    ],
    "WA": [
        _p("AAA9999", desc="Washington: 3 alpha + 4 digit"),
    ],
    "WV": [
        _p("9AA999", desc="West Virginia: digit + 2 alpha + 3 digit"),
        _p("AAA999", desc="West Virginia alt"),
    ],
    "WI": [
        _p("AAA9999", desc="Wisconsin: 3 alpha + 4 digit"),
        _p("999AAA", desc="Wisconsin alt"),
    ],
    "WY": [
        _p("99999", desc="Wyoming: county digit + 4 digit"),
        _p("999999", desc="Wyoming 6-digit"),
    ],
}


# ═══════════════════════════════════════════════════════════════════════════
# Validation & generation API
# ═══════════════════════════════════════════════════════════════════════════

def get_patterns(state: str) -> list[PlatePattern]:
    """Get all plate patterns for a state (2-letter code, uppercase)."""
    state = state.upper()
    if state not in STATE_FORMATS:
        raise ValueError(f"Unknown state: {state}. Use 2-letter code (e.g., 'CA')")
    return STATE_FORMATS[state]


def validate_plate(text: str, state: str | None = None) -> list[str]:
    """Check if text is a plausible plate string.

    Args:
        text: Plate string to validate (separators stripped automatically).
        state: If provided, validate against this state only.
                If None, check all states and return matches.

    Returns:
        List of state codes where this text is a valid plate format.
        Empty list = not plausible for any state.
    """
    clean = text.upper().replace(" ", "").replace("-", "").replace("·", "")
    matches = []

    states_to_check = [state.upper()] if state else sorted(STATE_FORMATS.keys())
    for st in states_to_check:
        for pattern in STATE_FORMATS.get(st, []):
            if pattern.validate(clean):
                matches.append(st)
                break  # one match per state is enough
    return matches


def is_plausible_plate(text: str, state: str | None = None) -> bool:
    """Return True if text matches any known plate format."""
    return len(validate_plate(text, state)) > 0


def generate_plate(state: str, seed: int | None = None) -> str:
    """Generate a random plausible plate for a given state.

    Uses the first (most common) pattern for the state.
    """
    patterns = get_patterns(state)
    rng = random.Random(seed)
    return patterns[0].generate(rng)


def generate_plates_multi_state(
    states: Sequence[str] | None = None,
    count_per_state: int = 1,
    seed: int | None = None,
) -> dict[str, list[str]]:
    """Generate plates for multiple states.

    Args:
        states: List of state codes. None = all 50 + DC.
        count_per_state: How many plates per state.
        seed: Random seed.

    Returns:
        Dict mapping state code to list of generated plate strings.
    """
    if states is None:
        states = sorted(STATE_FORMATS.keys())
    rng = random.Random(seed)
    result = {}
    for st in states:
        patterns = get_patterns(st)
        plates = []
        for _ in range(count_per_state):
            pattern = rng.choice(patterns)
            plates.append(pattern.generate(rng))
        result[st] = plates
    return result


def constrain_misread(
    original_plate: str,
    misread: str,
    state: str | None = None,
) -> bool:
    """Check if a misread would produce a plausible plate for any state.

    This is the key constraint for adversarial research: a misread that
    produces an implausible string (wrong length, wrong format) would be
    discarded by Flock's validation layer.  Only misreads that look like
    real plates from *some* state survive into the database.

    Args:
        original_plate: The actual plate text.
        misread: The corrupted OCR read.
        state: If provided, constrain to this state only.

    Returns:
        True if the misread is plausible (would survive validation).
    """
    return is_plausible_plate(misread, state)


# ═══════════════════════════════════════════════════════════════════════════
# Confusion-aware generation
# ═══════════════════════════════════════════════════════════════════════════

# Import confusion pairs from decal_generator for cross-referencing
_CONFUSION_PAIRS: dict[str, list[str]] = {
    "0": ["O", "D", "Q"], "O": ["0", "D", "Q"],
    "D": ["0", "O", "Q"], "Q": ["0", "O", "D"],
    "1": ["I", "L"], "I": ["1", "L"], "L": ["1", "I"],
    "8": ["B"], "B": ["8"],
    "5": ["S"], "S": ["5"],
    "2": ["Z"], "Z": ["2"],
    "6": ["G"], "G": ["6"],
}


def generate_confusion_plate(
    state: str,
    seed: int | None = None,
) -> str:
    """Generate a plate maximally loaded with confusable characters.

    Produces a valid plate for the given state where every possible
    character position uses a character from a confusion pair.
    """
    patterns = get_patterns(state)
    pattern = patterns[0]
    rng = random.Random(seed)

    # Characters that belong to confusion pairs, split by type
    confusable_alpha = [c for c in _CONFUSION_PAIRS if c.isalpha()]
    confusable_digit = [c for c in _CONFUSION_PAIRS if c.isdigit()]

    parts = []
    for seg in pattern.segments:
        chars = []
        for _ in range(seg.length):
            if seg.type == "alpha":
                chars.append(rng.choice(confusable_alpha))
            elif seg.type == "digit":
                chars.append(rng.choice(confusable_digit))
            else:  # alphanumeric
                chars.append(rng.choice(list(_CONFUSION_PAIRS.keys())))
        parts.append("".join(chars))
    return "".join(parts)


def enumerate_plausible_misreads(
    plate: str,
    state: str | None = None,
    max_substitutions: int = 2,
) -> list[str]:
    """Generate all single/double confusion-pair substitutions that remain plausible.

    For a plate like "BOO8008", returns all 1- and 2-character substitutions
    using confusion pairs that still match a valid plate format.

    Args:
        plate: Original plate text.
        state: Constrain to this state (None = any state).
        max_substitutions: Max simultaneous character swaps (1 or 2).

    Returns:
        List of plausible misreads (deduplicated).
    """
    plate = plate.upper()
    misreads = set()

    # Single substitutions
    for i, ch in enumerate(plate):
        if ch in _CONFUSION_PAIRS:
            for alt in _CONFUSION_PAIRS[ch]:
                candidate = plate[:i] + alt + plate[i + 1:]
                if candidate != plate and is_plausible_plate(candidate, state):
                    misreads.add(candidate)

    # Double substitutions
    if max_substitutions >= 2:
        for i in range(len(plate)):
            if plate[i] not in _CONFUSION_PAIRS:
                continue
            for alt_i in _CONFUSION_PAIRS[plate[i]]:
                for j in range(i + 1, len(plate)):
                    if plate[j] not in _CONFUSION_PAIRS:
                        continue
                    for alt_j in _CONFUSION_PAIRS[plate[j]]:
                        candidate = plate[:i] + alt_i + plate[i + 1:j] + alt_j + plate[j + 1:]
                        if candidate != plate and is_plausible_plate(candidate, state):
                            misreads.add(candidate)

    return sorted(misreads)


# ═══════════════════════════════════════════════════════════════════════════
# Stats & coverage info
# ═══════════════════════════════════════════════════════════════════════════

def coverage_summary() -> dict:
    """Return summary statistics about plate format coverage."""
    total_patterns = sum(len(pats) for pats in STATE_FORMATS.values())
    lengths = set()
    for pats in STATE_FORMATS.values():
        for p in pats:
            lengths.add(p.total_length)

    return {
        "states_covered": len(STATE_FORMATS),
        "total_patterns": total_patterns,
        "plate_lengths": sorted(lengths),
        "states": sorted(STATE_FORMATS.keys()),
    }
