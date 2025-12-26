"""
Centralized path constants for Beopsuny scripts.

All scripts should import paths from here:
    from common.paths import SKILL_DIR, CONFIG_PATH, ASSETS_DIR

This module provides a single source of truth for all file paths,
making directory structure changes easier to manage.
"""
from pathlib import Path

# Base directories
SCRIPT_DIR = Path(__file__).parent.parent  # scripts/
SKILL_DIR = SCRIPT_DIR.parent               # beopsuny/

# Configuration (secrets only)
CONFIG_DIR = SKILL_DIR / "config"
CONFIG_PATH = CONFIG_DIR / "settings.yaml"

# Static assets (Agent Skills spec: assets/)
ASSETS_DIR = SKILL_DIR / "assets"
LAW_INDEX_PATH = ASSETS_DIR / "law_index.yaml"
LEGAL_TERMS_PATH = ASSETS_DIR / "legal_terms.yaml"
CLAUSE_REFS_PATH = ASSETS_DIR / "clause_references.yaml"
FORMS_PATH = ASSETS_DIR / "forms.yaml"
CHECKLISTS_DIR = ASSETS_DIR / "checklists"

# Reference documentation (Agent Skills spec: references/)
REFERENCES_DIR = SKILL_DIR / "references"

# Runtime data (not included in skill ZIP)
DATA_DIR = SKILL_DIR / "data"
DATA_RAW_DIR = DATA_DIR / "raw"
DATA_PARSED_DIR = DATA_DIR / "parsed"
DATA_BILLS_DIR = DATA_DIR / "bills"
DATA_POLICY_DIR = DATA_DIR / "policy"

# API defaults (moved from settings.yaml)
API_BASE_URL = "http://www.law.go.kr/DRF"
API_TIMEOUT = 30
API_DEFAULT_DISPLAY = 20
