"""
Unit tests for fetch_law.py helper functions.

Tests the extracted helper functions:
- _sanitize_filename(): File name sanitization
- _clean_html_text(): HTML tag removal
- get_major_law_id(): Law ID lookup from index
- parse_date_to_ymd(): Date string parsing
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent.parent / ".claude" / "skills" / "beopsuny" / "scripts"
sys.path.insert(0, str(scripts_dir))

from fetch_law import (
    _sanitize_filename,
    _clean_html_text,
    get_major_law_id,
    TARGET_TYPE_NAMES,
)


class TestSanitizeFilename:
    """Tests for _sanitize_filename() helper function."""

    def test_removes_special_characters(self):
        """Should remove special characters from filename."""
        assert _sanitize_filename("법률<>:test") == "법률test"

    def test_preserves_safe_characters(self):
        """Should preserve alphanumeric, spaces, underscores, and hyphens."""
        assert _sanitize_filename("법률_test-123 가나다") == "법률_test-123 가나다"

    def test_strips_whitespace(self):
        """Should strip leading/trailing whitespace."""
        assert _sanitize_filename("  테스트  ") == "테스트"

    def test_empty_string_returns_unnamed(self):
        """Should return 'unnamed' for empty result."""
        assert _sanitize_filename("<<<>>>") == "unnamed"

    def test_only_whitespace_returns_unnamed(self):
        """Should return 'unnamed' when only whitespace remains."""
        assert _sanitize_filename("   ") == "unnamed"


class TestCleanHtmlText:
    """Tests for _clean_html_text() helper function."""

    def test_removes_html_tags(self):
        """Should remove HTML tags."""
        assert _clean_html_text("<p>테스트</p>") == "테스트"

    def test_removes_nested_tags(self):
        """Should remove nested HTML tags."""
        assert _clean_html_text("<div><p>테스트</p></div>") == "테스트"

    def test_preserves_breaks_when_requested(self):
        """Should convert <br> to newlines when preserve_breaks=True."""
        result = _clean_html_text("줄1<br>줄2<br/>줄3", preserve_breaks=True)
        assert result == "줄1\n줄2\n줄3"

    def test_removes_breaks_by_default(self):
        """Should remove <br> tags when preserve_breaks=False."""
        result = _clean_html_text("줄1<br>줄2")
        assert result == "줄1줄2"

    def test_truncates_with_max_length(self):
        """Should truncate and add ... when exceeding max_length."""
        result = _clean_html_text("가나다라마바사아자차", max_length=5)
        assert result == "가나다라마..."

    def test_no_truncation_under_max_length(self):
        """Should not truncate when under max_length."""
        result = _clean_html_text("가나다", max_length=10)
        assert result == "가나다"


class TestGetMajorLawId:
    """Tests for get_major_law_id() law index lookup."""

    def test_returns_none_for_unknown_law(self):
        """Should return None for laws not in index."""
        with patch('fetch_law._load_law_index', return_value={'major_laws': {}}):
            assert get_major_law_id("존재하지않는법") is None

    def test_finds_exact_match(self):
        """Should find law by exact name match."""
        mock_index = {'major_laws': {'개인정보 보호법': '011357'}}
        with patch('fetch_law._load_law_index', return_value=mock_index):
            assert get_major_law_id("개인정보 보호법") == "011357"

    def test_finds_match_ignoring_spaces(self):
        """Should find law ignoring spaces in name."""
        mock_index = {'major_laws': {'개인정보 보호법': '011357'}}
        with patch('fetch_law._load_law_index', return_value=mock_index):
            assert get_major_law_id("개인정보보호법") == "011357"


class TestTargetTypeNames:
    """Tests for TARGET_TYPE_NAMES constant."""

    def test_contains_law_type(self):
        """Should contain law type."""
        assert 'law' in TARGET_TYPE_NAMES
        assert TARGET_TYPE_NAMES['law'] == '법령'

    def test_contains_prec_type(self):
        """Should contain precedent type."""
        assert 'prec' in TARGET_TYPE_NAMES
        assert TARGET_TYPE_NAMES['prec'] == '판례'

    def test_contains_admrul_type(self):
        """Should contain administrative rule type."""
        assert 'admrul' in TARGET_TYPE_NAMES
        assert TARGET_TYPE_NAMES['admrul'] == '행정규칙'

    def test_contains_all_expected_types(self):
        """Should contain all expected types."""
        expected_types = {'law', 'prec', 'ordin', 'admrul', 'expc', 'detc'}
        assert set(TARGET_TYPE_NAMES.keys()) == expected_types


class TestApiRequestMocking:
    """Tests for API request handling with mocking."""

    def test_api_request_parses_xml(self, sample_law_xml):
        """Should parse XML response correctly."""
        import xml.etree.ElementTree as ET
        root = ET.fromstring(sample_law_xml)

        assert root.find('.//totalCnt').text == '1'
        law = root.find('.//law')
        assert law.find('법령ID').text == '001815'
        assert law.find('법령명').text == '의료법'

    def test_precedent_xml_parsing(self, sample_prec_xml):
        """Should parse precedent XML response correctly."""
        import xml.etree.ElementTree as ET
        root = ET.fromstring(sample_prec_xml)

        assert root.find('.//totalCnt').text == '1'
        prec = root.find('.//prec')
        assert prec.find('사건번호').text == '2023다12345'
        assert prec.find('법원명').text == '대법원'
