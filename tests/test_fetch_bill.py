"""
Unit tests for fetch_bill.py helper functions.

Tests the extracted helper functions:
- _extract_committee(): Committee name extraction with fallback
- _build_bill_dict(): Standardized bill dictionary construction
"""
import sys
from pathlib import Path

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent.parent / ".claude" / "skills" / "beopsuny" / "scripts"
sys.path.insert(0, str(scripts_dir))

from fetch_bill import _extract_committee, _build_bill_dict


class TestExtractCommittee:
    """Tests for _extract_committee() helper function."""

    def test_prefers_curr_committee(self):
        """CURR_COMMITTEE should be preferred over COMMITTEE."""
        item = {"CURR_COMMITTEE": "법제사법위원회", "COMMITTEE": "행정안전위원회"}
        assert _extract_committee(item) == "법제사법위원회"

    def test_falls_back_to_committee(self):
        """When CURR_COMMITTEE is empty, should use COMMITTEE."""
        item = {"CURR_COMMITTEE": "", "COMMITTEE": "행정안전위원회"}
        assert _extract_committee(item) == "행정안전위원회"

    def test_falls_back_when_curr_missing(self):
        """When CURR_COMMITTEE is missing, should use COMMITTEE."""
        item = {"COMMITTEE": "기획재정위원회"}
        assert _extract_committee(item) == "기획재정위원회"

    def test_returns_empty_when_both_missing(self):
        """When both fields are missing, should return empty string."""
        item = {}
        assert _extract_committee(item) == ""

    def test_returns_empty_when_both_empty(self):
        """When both fields are empty strings, should return empty string."""
        item = {"CURR_COMMITTEE": "", "COMMITTEE": ""}
        assert _extract_committee(item) == ""

    def test_handles_none_values(self):
        """Should handle None values correctly."""
        item = {"CURR_COMMITTEE": None, "COMMITTEE": "산업통상자원위원회"}
        # None is falsy, so should fall back to COMMITTEE
        assert _extract_committee(item) == "산업통상자원위원회"


class TestBuildBillDict:
    """Tests for _build_bill_dict() helper function."""

    def test_basic_fields(self):
        """Should extract basic fields correctly."""
        item = {
            "BILL_NO": "2201234",
            "BILL_NAME": "상법 일부개정법률안",
            "RST_PROPOSER": "홍길동의원",
            "PROPOSE_DT": "2024-01-15",
            "CURR_COMMITTEE": "법제사법위원회",
        }
        result = _build_bill_dict(item)

        assert result["bill_no"] == "2201234"
        assert result["name"] == "상법 일부개정법률안"
        assert result["proposer"] == "홍길동의원"
        assert result["propose_date"] == "2024-01-15"
        assert result["committee"] == "법제사법위원회"

    def test_proposer_fallback(self):
        """Should fall back to PROPOSER when RST_PROPOSER is empty."""
        item = {
            "BILL_NO": "2201234",
            "BILL_NAME": "민법 일부개정법률안",
            "RST_PROPOSER": "",
            "PROPOSER": "정부",
            "PROPOSE_DT": "2024-02-01",
        }
        result = _build_bill_dict(item)
        assert result["proposer"] == "정부"

    def test_excludes_bill_id_by_default(self):
        """Should not include bill_id by default."""
        item = {
            "BILL_ID": "PRC_ABC123",
            "BILL_NO": "2201234",
            "BILL_NAME": "테스트 법률안",
            "PROPOSE_DT": "2024-01-01",
        }
        result = _build_bill_dict(item)
        assert "bill_id" not in result

    def test_includes_bill_id_when_requested(self):
        """Should include bill_id when include_bill_id=True."""
        item = {
            "BILL_ID": "PRC_ABC123",
            "BILL_NO": "2201234",
            "BILL_NAME": "테스트 법률안",
            "PROPOSE_DT": "2024-01-01",
        }
        result = _build_bill_dict(item, include_bill_id=True)
        assert result["bill_id"] == "PRC_ABC123"

    def test_excludes_proc_result_by_default(self):
        """Should not include proc_result by default."""
        item = {
            "BILL_NO": "2201234",
            "BILL_NAME": "테스트 법률안",
            "PROPOSE_DT": "2024-01-01",
            "PROC_RESULT": "원안가결",
        }
        result = _build_bill_dict(item)
        assert "proc_result" not in result

    def test_includes_proc_result_when_requested(self):
        """Should include proc_result when include_proc_result=True."""
        item = {
            "BILL_NO": "2201234",
            "BILL_NAME": "테스트 법률안",
            "PROPOSE_DT": "2024-01-01",
            "PROC_RESULT": "원안가결",
        }
        result = _build_bill_dict(item, include_proc_result=True)
        assert result["proc_result"] == "원안가결"

    def test_includes_both_optional_fields(self):
        """Should include both bill_id and proc_result when both requested."""
        item = {
            "BILL_ID": "PRC_XYZ789",
            "BILL_NO": "2209999",
            "BILL_NAME": "통합 테스트 법률안",
            "RST_PROPOSER": "테스트의원",
            "PROPOSE_DT": "2024-06-01",
            "PROC_RESULT": "수정가결",
            "CURR_COMMITTEE": "환경노동위원회",
        }
        result = _build_bill_dict(item, include_bill_id=True, include_proc_result=True)

        assert result["bill_id"] == "PRC_XYZ789"
        assert result["bill_no"] == "2209999"
        assert result["name"] == "통합 테스트 법률안"
        assert result["proposer"] == "테스트의원"
        assert result["propose_date"] == "2024-06-01"
        assert result["proc_result"] == "수정가결"
        assert result["committee"] == "환경노동위원회"

    def test_handles_missing_fields(self):
        """Should handle missing fields with empty string defaults."""
        item = {}
        result = _build_bill_dict(item)

        assert result["bill_no"] == ""
        assert result["name"] == ""
        assert result["proposer"] == ""
        assert result["propose_date"] == ""
        assert result["committee"] == ""

    def test_proposer_fallback_from_none(self):
        """Should fall back to PROPOSER when RST_PROPOSER is None."""
        item = {
            "BILL_NO": "2201234",
            "BILL_NAME": "민법 일부개정법률안",
            "RST_PROPOSER": None,
            "PROPOSER": "정부",
            "PROPOSE_DT": "2024-02-01",
        }
        result = _build_bill_dict(item)
        assert result["proposer"] == "정부"

    def test_bill_id_missing_when_requested(self):
        """Should return empty string for bill_id when key is missing but requested."""
        item = {
            "BILL_NO": "2201234",
            "BILL_NAME": "테스트 법률안",
            "PROPOSE_DT": "2024-01-01",
            # BILL_ID is intentionally missing
        }
        result = _build_bill_dict(item, include_bill_id=True)
        assert result["bill_id"] == ""

    def test_proc_result_missing_when_requested(self):
        """Should return empty string for proc_result when key is missing but requested."""
        item = {
            "BILL_NO": "2201234",
            "BILL_NAME": "테스트 법률안",
            "PROPOSE_DT": "2024-01-01",
            # PROC_RESULT is intentionally missing
        }
        result = _build_bill_dict(item, include_proc_result=True)
        assert result["proc_result"] == ""

    def test_proposer_only_uses_proposer_field(self):
        """With proposer_only=True, should use only PROPOSER field (for pending bills API)."""
        item = {
            "BILL_NO": "2201234",
            "BILL_NAME": "계류 의안 테스트",
            "RST_PROPOSER": "홍길동의원",
            "PROPOSER": "정부",
            "PROPOSE_DT": "2024-03-01",
        }
        result = _build_bill_dict(item, proposer_only=True)
        # Should use PROPOSER, not RST_PROPOSER
        assert result["proposer"] == "정부"

    def test_proposer_only_false_prefers_rst_proposer(self):
        """With proposer_only=False (default), should prefer RST_PROPOSER."""
        item = {
            "BILL_NO": "2201234",
            "BILL_NAME": "일반 의안 테스트",
            "RST_PROPOSER": "홍길동의원",
            "PROPOSER": "정부",
            "PROPOSE_DT": "2024-03-01",
        }
        result = _build_bill_dict(item, proposer_only=False)
        # Should use RST_PROPOSER
        assert result["proposer"] == "홍길동의원"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
