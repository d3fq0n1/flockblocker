"""Shared pytest fixtures for FlockBlocker OCR testing."""

import pytest
from pathlib import Path


FIXTURES_DIR = Path(__file__).parent / "fixtures"
PLATES_DIR = FIXTURES_DIR / "plates"
DECALS_DIR = FIXTURES_DIR / "decals"
COMPOSITES_DIR = FIXTURES_DIR / "composites"


@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR


@pytest.fixture
def plates_dir():
    return PLATES_DIR


@pytest.fixture
def decals_dir():
    return DECALS_DIR


@pytest.fixture
def composites_dir():
    return COMPOSITES_DIR
