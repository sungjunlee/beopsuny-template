"""
Unit tests for fetch_policy.py helper functions.

Tests the policy fetcher:
- RSS feed parsing
- OC code configuration
- Ministry code mappings
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent.parent / ".claude" / "skills" / "beopsuny" / "scripts"
sys.path.insert(0, str(scripts_dir))

from fetch_policy import (
    RSS_FEEDS,
    API_ENDPOINTS,
    get_oc_code,
    ensure_data_dir,
)


class TestRSSFeeds:
    """Tests for RSS_FEEDS configuration."""

    def test_contains_ftc(self):
        """Should contain Fair Trade Commission feed."""
        assert 'ftc' in RSS_FEEDS
        assert RSS_FEEDS['ftc']['name'] == '공정거래위원회'
        assert 'url' in RSS_FEEDS['ftc']

    def test_contains_moel(self):
        """Should contain Ministry of Employment and Labor feed."""
        assert 'moel' in RSS_FEEDS
        assert RSS_FEEDS['moel']['name'] == '고용노동부'

    def test_contains_pipc(self):
        """Should contain Personal Information Protection Commission feed."""
        assert 'pipc' in RSS_FEEDS
        assert RSS_FEEDS['pipc']['name'] == '개인정보보호위원회'

    def test_all_feeds_have_keywords(self):
        """All feeds should have keyword filters."""
        for code, feed in RSS_FEEDS.items():
            assert 'keywords' in feed, f"Feed {code} missing keywords"
            assert isinstance(feed['keywords'], list), f"Feed {code} keywords should be list"
            assert len(feed['keywords']) > 0, f"Feed {code} should have at least one keyword"


class TestAPIEndpoints:
    """Tests for API_ENDPOINTS configuration."""

    def test_contains_moel_interpret(self):
        """Should contain MOEL interpretation endpoint."""
        assert 'moel_interpret' in API_ENDPOINTS
        assert 'law.go.kr' in API_ENDPOINTS['moel_interpret']

    def test_contains_legislative(self):
        """Should contain legislative notice endpoint."""
        assert 'legislative' in API_ENDPOINTS


class TestGetOcCode:
    """Tests for get_oc_code() configuration loading."""

    def test_returns_env_var_when_set(self):
        """Should return OC code from environment variable."""
        with patch.dict('os.environ', {'BEOPSUNY_OC_CODE': 'test_oc_code'}):
            assert get_oc_code() == 'test_oc_code'

    def test_raises_when_not_configured(self):
        """Should raise ValueError when OC code not found."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('fetch_policy._load_config_file', return_value={}):
                with pytest.raises(ValueError) as exc_info:
                    get_oc_code()
                assert 'OC code not found' in str(exc_info.value)

    def test_falls_back_to_config_file(self):
        """Should fall back to config file when env var not set."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('fetch_policy._load_config_file', return_value={'oc_code': 'file_oc_code'}):
                assert get_oc_code() == 'file_oc_code'


class TestRSSParsing:
    """Tests for RSS feed parsing."""

    def test_parse_rss_xml(self, sample_rss_feed):
        """Should parse RSS XML correctly."""
        import xml.etree.ElementTree as ET
        root = ET.fromstring(sample_rss_feed)

        channel = root.find('channel')
        assert channel is not None
        assert channel.find('title').text == '공정거래위원회 보도자료'

        items = channel.findall('item')
        assert len(items) == 1
        assert '과징금' in items[0].find('title').text


class TestEnsureDataDir:
    """Tests for ensure_data_dir() utility."""

    def test_creates_directory(self, tmp_path):
        """Should create data directory if not exists."""
        with patch('fetch_policy.DATA_POLICY_DIR', tmp_path / 'policy'):
            ensure_data_dir()
            assert (tmp_path / 'policy').exists()

    def test_handles_existing_directory(self, tmp_path):
        """Should not fail if directory already exists."""
        test_dir = tmp_path / 'existing'
        test_dir.mkdir()
        with patch('fetch_policy.DATA_POLICY_DIR', test_dir):
            ensure_data_dir()  # Should not raise
            assert test_dir.exists()
