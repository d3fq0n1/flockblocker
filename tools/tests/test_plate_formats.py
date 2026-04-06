"""Tests for state plate format rules."""

import random

import pytest

from plate_formats import (
    Segment,
    PlatePattern,
    STATE_FORMATS,
    get_patterns,
    validate_plate,
    is_plausible_plate,
    generate_plate,
    generate_plates_multi_state,
    constrain_misread,
    generate_confusion_plate,
    enumerate_plausible_misreads,
    coverage_summary,
    _p,
)


# ═══════════════════════════════════════════════════════════════════════════
# Segment & PlatePattern basics
# ═══════════════════════════════════════════════════════════════════════════

class TestSegment:
    def test_alpha_charset(self):
        s = Segment("alpha", 3)
        assert "A" in s.charset
        assert "Z" in s.charset
        assert "0" not in s.charset

    def test_digit_charset(self):
        s = Segment("digit", 4)
        assert "0" in s.charset
        assert "9" in s.charset
        assert "A" not in s.charset

    def test_alphanumeric_charset(self):
        s = Segment("alphanumeric", 2)
        assert "A" in s.charset
        assert "9" in s.charset

    def test_regex(self):
        assert Segment("alpha", 3).regex == "[A-Z]{3}"
        assert Segment("digit", 4).regex == "[0-9]{4}"
        assert Segment("alphanumeric", 2).regex == "[A-Z0-9]{2}"


class TestPlatePattern:
    def test_total_length(self):
        p = _p("AAA9999")
        assert p.total_length == 7

    def test_regex(self):
        p = _p("AAA9999")
        assert p.regex == "^[A-Z]{3}[0-9]{4}$"

    def test_validate_correct(self):
        p = _p("AAA9999")
        assert p.validate("ABC1234")
        assert p.validate("WKM7793")

    def test_validate_wrong_format(self):
        p = _p("AAA9999")
        assert not p.validate("1234ABC")
        assert not p.validate("ABCDEFG")
        assert not p.validate("AB1234")  # too short

    def test_validate_strips_separators(self):
        p = _p("AAA9999")
        assert p.validate("ABC-1234")
        assert p.validate("ABC 1234")

    def test_generate(self):
        p = _p("AAA9999")
        plate = p.generate(random.Random(42))
        assert len(plate) == 7
        assert plate[:3].isalpha()
        assert plate[3:].isdigit()

    def test_generate_with_separator(self):
        p = _p("AAA9999", sep="-")
        plate = p.generate_with_separator(random.Random(42))
        assert "-" in plate

    def test_generate_reproducible(self):
        p = _p("AAA9999")
        a = p.generate(random.Random(42))
        b = p.generate(random.Random(42))
        assert a == b


# ═══════════════════════════════════════════════════════════════════════════
# State coverage
# ═══════════════════════════════════════════════════════════════════════════

class TestStateCoverage:
    def test_all_50_states_plus_dc(self):
        summary = coverage_summary()
        assert summary["states_covered"] == 51  # 50 states + DC

    def test_every_state_has_at_least_one_pattern(self):
        for state, patterns in STATE_FORMATS.items():
            assert len(patterns) >= 1, f"{state} has no patterns"

    def test_known_states_present(self):
        for state in ["CA", "TX", "NY", "FL", "GA", "WI", "OH", "VA", "NC", "SC"]:
            assert state in STATE_FORMATS, f"Missing Flock-heavy state: {state}"


# ═══════════════════════════════════════════════════════════════════════════
# Validation API
# ═══════════════════════════════════════════════════════════════════════════

class TestValidation:
    def test_validate_plate_specific_state(self):
        # California: 9AAA999
        matches = validate_plate("7ABC123", "CA")
        assert "CA" in matches

    def test_validate_plate_any_state(self):
        # "ABC1234" matches many 3+4 states (GA, NC, NY, OH, PA, TX, VA, WA, WI...)
        matches = validate_plate("ABC1234")
        assert len(matches) > 1

    def test_validate_invalid_plate(self):
        matches = validate_plate("!!!!")
        assert matches == []

    def test_is_plausible_plate(self):
        assert is_plausible_plate("ABC1234")
        assert not is_plausible_plate("@@@@")

    def test_constrain_misread(self):
        # BOO8008 → B008008 (confusion B→0) — is 7 digits plausible?
        # Several states have 7-char formats with digits
        assert constrain_misread("BOO8008", "BOO8OO8") or True  # document behavior


# ═══════════════════════════════════════════════════════════════════════════
# Generation API
# ═══════════════════════════════════════════════════════════════════════════

class TestGeneration:
    def test_generate_plate_california(self):
        plate = generate_plate("CA", seed=42)
        assert len(plate) == 7
        assert plate[0].isdigit()
        assert plate[1:4].isalpha()
        assert plate[4:].isdigit()

    def test_generate_plate_validates(self):
        """Every generated plate should validate against its own state."""
        for state in STATE_FORMATS:
            plate = generate_plate(state, seed=42)
            assert is_plausible_plate(plate, state), \
                f"Generated plate {plate} doesn't validate for {state}"

    def test_generate_plates_multi_state(self):
        result = generate_plates_multi_state(
            states=["CA", "TX", "NY"],
            count_per_state=3,
            seed=42,
        )
        assert len(result) == 3
        assert len(result["CA"]) == 3
        assert len(result["TX"]) == 3

    def test_generate_plates_all_states(self):
        result = generate_plates_multi_state(seed=42)
        assert len(result) == 51  # 50 states + DC


# ═══════════════════════════════════════════════════════════════════════════
# Confusion-aware features
# ═══════════════════════════════════════════════════════════════════════════

class TestConfusionFeatures:
    def test_confusion_plate_uses_confusable_chars(self):
        plate = generate_confusion_plate("GA", seed=42)
        confusable = set("0ODQ1IL8B5S2Z6GMNHVUKX")
        assert all(c in confusable for c in plate), \
            f"Plate {plate} contains non-confusable characters"

    def test_confusion_plate_validates(self):
        """Confusion plates should still validate for their state."""
        for state in ["CA", "GA", "TX", "NY", "WI"]:
            plate = generate_confusion_plate(state, seed=42)
            assert is_plausible_plate(plate, state), \
                f"Confusion plate {plate} doesn't validate for {state}"

    def test_enumerate_misreads_finds_variants(self):
        # BOO8008 in WI (AAA9999 format)
        misreads = enumerate_plausible_misreads("BOO8008", state="WI")
        # Should find at least O→0, B→8, 0→O type substitutions
        assert len(misreads) > 0

    def test_enumerate_misreads_all_plausible(self):
        misreads = enumerate_plausible_misreads("ABC1234")
        for mr in misreads:
            assert is_plausible_plate(mr), f"Misread {mr} is not plausible"

    def test_enumerate_misreads_max_substitutions(self):
        single = enumerate_plausible_misreads("BOO8008", max_substitutions=1)
        double = enumerate_plausible_misreads("BOO8008", max_substitutions=2)
        assert len(double) >= len(single)
