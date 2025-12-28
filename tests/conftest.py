"""
Pytest fixtures and configuration for beopsuny tests.
"""
import sys
from pathlib import Path

import pytest

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent.parent / ".claude" / "skills" / "beopsuny" / "scripts"
common_dir = scripts_dir / "common"
sys.path.insert(0, str(scripts_dir))
sys.path.insert(0, str(common_dir))

# Data directories
ASSETS_DIR = Path(__file__).parent.parent / ".claude" / "skills" / "beopsuny" / "assets"
DATA_DIR = Path(__file__).parent.parent / ".claude" / "skills" / "beopsuny" / "data"
# law_index.yaml is in assets, not data
LAW_INDEX_PATH = ASSETS_DIR / "law_index.yaml"


@pytest.fixture
def sample_law_xml():
    """Sample XML response from law.go.kr API."""
    return """<?xml version="1.0" encoding="UTF-8"?>
    <LawSearch>
        <totalCnt>1</totalCnt>
        <law>
            <법령ID>001815</법령ID>
            <법령명>의료법</법령명>
            <법령명한글>의료법</법령명한글>
            <시행일자>20240101</시행일자>
            <소관부처명>보건복지부</소관부처명>
        </law>
    </LawSearch>"""


@pytest.fixture
def sample_prec_xml():
    """Sample XML response for court precedent search."""
    return """<?xml version="1.0" encoding="UTF-8"?>
    <PrecSearch>
        <totalCnt>1</totalCnt>
        <prec>
            <판례일련번호>123456</판례일련번호>
            <사건번호>2023다12345</사건번호>
            <사건명>손해배상(기)</사건명>
            <선고일자>20231215</선고일자>
            <법원명>대법원</법원명>
        </prec>
    </PrecSearch>"""


@pytest.fixture
def sample_rss_feed():
    """Sample RSS feed content."""
    return """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>공정거래위원회 보도자료</title>
            <item>
                <title>불공정거래 과징금 부과</title>
                <link>https://example.com/news/1</link>
                <pubDate>Mon, 25 Dec 2024 10:00:00 +0900</pubDate>
            </item>
        </channel>
    </rss>"""


@pytest.fixture
def permits_yaml_path():
    """Path to permits.yaml file."""
    return ASSETS_DIR / "permits.yaml"


@pytest.fixture
def law_index_yaml_path():
    """Path to law_index.yaml file."""
    return LAW_INDEX_PATH


@pytest.fixture
def checklists_dir():
    """Path to checklists directory."""
    return ASSETS_DIR / "checklists"
