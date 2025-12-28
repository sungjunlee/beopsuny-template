#!/usr/bin/env python3
"""
허가/신고 데이터 검증 스크립트

permits.yaml의 데이터 무결성을 검증합니다:
- law_id가 law_index.yaml에 존재하는지 확인
- 관련 체크리스트가 존재하는지 확인
- 필수 필드 누락 여부 확인

Usage:
    python validate_permits.py                # 전체 검증
    python validate_permits.py --markdown     # 마크다운 리포트 출력
    python validate_permits.py --json         # JSON 출력

Exit codes:
    0: 모든 검증 통과 (경고만 있는 경우 포함)
    1: 필수 검증 실패 항목 발견 (issues)
    2: 에러 발생 (파일 읽기 실패 등)
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

import yaml

# 경로 설정: common.paths에서 중앙 관리
sys.path.insert(0, str(Path(__file__).parent.parent))
from common.paths import ASSETS_DIR, CHECKLISTS_DIR, LAW_INDEX_PATH, PERMITS_PATH

# 필수 필드 정의
REQUIRED_FIELDS = ["id", "name", "type", "category", "law", "authority"]
RECOMMENDED_FIELDS = ["documents", "processing", "priority", "gov24_url"]


def load_permits() -> Optional[dict]:
    """permits.yaml 로드"""
    if not PERMITS_PATH.exists():
        print(f"Error: {PERMITS_PATH} not found", file=sys.stderr)
        return None

    try:
        with open(PERMITS_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except (yaml.YAMLError, OSError, UnicodeDecodeError) as e:
        print(f"Error loading permits.yaml: {e}", file=sys.stderr)
        return None


def load_law_index() -> dict:
    """law_index.yaml 로드"""
    if not LAW_INDEX_PATH.exists():
        print(f"Warning: {LAW_INDEX_PATH} not found - law_id 검증 건너뜀", file=sys.stderr)
        return {}

    try:
        with open(LAW_INDEX_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except (yaml.YAMLError, OSError, UnicodeDecodeError) as e:
        print(f"Warning: law_index.yaml 읽기 실패: {e}", file=sys.stderr)
        return {}

    return data.get("major_laws", {})


def get_available_checklists() -> set:
    """사용 가능한 체크리스트 ID 목록"""
    checklists = set()
    if not CHECKLISTS_DIR.exists():
        print(f"Warning: {CHECKLISTS_DIR} not found - 체크리스트 검증 건너뜀", file=sys.stderr)
        return checklists
    for f in CHECKLISTS_DIR.glob("*.yaml"):
        checklists.add(f.stem)
    return checklists


def validate_permit(permit: dict, law_index: dict, checklists: set) -> dict:
    """개별 허가 항목 검증"""
    issues = []
    warnings = []

    permit_id = permit.get("id", "unknown")
    permit_name = permit.get("name", "unknown")

    # 1. 필수 필드 확인
    for field in REQUIRED_FIELDS:
        if not permit.get(field):
            issues.append(f"필수 필드 누락: {field}")

    # 2. 권장 필드 확인
    for field in RECOMMENDED_FIELDS:
        if not permit.get(field):
            warnings.append(f"권장 필드 누락: {field}")

    # 3. law_id 검증
    law_info = permit.get("law")
    if law_info is None:
        law_id = None
        law_name = ""
    elif not isinstance(law_info, dict):
        issues.append(f"'law' 필드가 dict가 아님: {type(law_info).__name__}")
        law_id = None
        law_name = ""
    else:
        law_id = law_info.get("law_id")
        law_name = law_info.get("name") or law_info.get("short_name", "")

    if law_id:
        # law_index에서 찾기
        found = False
        for name, id_val in law_index.items():
            if str(id_val) == str(law_id):
                found = True
                break
        if not found:
            warnings.append(f"law_id '{law_id}'가 law_index.yaml에 없음")
    else:
        # law_name으로 매칭 시도
        if law_name:
            matched_id = None
            for name, id_val in law_index.items():
                if law_name in name or name in law_name:
                    matched_id = id_val
                    break
            if matched_id:
                warnings.append(f"law_id 누락 - 추천: {matched_id} ({law_name})")
            else:
                warnings.append(f"law_id 누락, 매칭 실패: {law_name}")

    # 4. 관련 체크리스트 검증
    related = permit.get("related_checklists", [])
    for checklist_id in related:
        if checklist_id not in checklists:
            warnings.append(f"체크리스트 '{checklist_id}'가 존재하지 않음")

    # 5. priority 값 검증
    priority = permit.get("priority")
    valid_priorities = ["critical", "high", "medium", "low"]
    if priority and priority not in valid_priorities:
        warnings.append(f"잘못된 priority 값: {priority}")

    # 6. type 값 검증
    permit_type = permit.get("type")
    valid_types = ["permit", "registration", "notification", "approval", "license"]
    if permit_type and permit_type not in valid_types:
        issues.append(f"잘못된 type 값: {permit_type}")

    return {
        "id": permit_id,
        "name": permit_name,
        "issues": issues,
        "warnings": warnings,
        "valid": len(issues) == 0,
    }


def validate_all(permits_data: dict, law_index: dict, checklists: set) -> list:
    """모든 허가 항목 검증"""
    results = []

    items = permits_data.get("items", [])
    for permit in items:
        result = validate_permit(permit, law_index, checklists)
        results.append(result)

    return results


def format_markdown(results: list, permits_data: dict) -> str:
    """마크다운 리포트 생성"""
    lines = []

    # 요약
    total = len(results)
    valid = sum(1 for r in results if r["valid"])
    with_warnings = sum(1 for r in results if r["warnings"])
    with_issues = sum(1 for r in results if r["issues"])

    lines.append("## 허가/신고 데이터 검증 리포트")
    lines.append("")
    lines.append(f"**검증일**: {permits_data.get('last_updated', 'N/A')}")
    lines.append(f"**총 항목**: {total}개")
    lines.append(f"**유효**: {valid}개 | **이슈**: {with_issues}개 | **경고**: {with_warnings}개")
    lines.append("")

    # 이슈 있는 항목
    if with_issues > 0:
        lines.append("### 이슈 (수정 필요)")
        lines.append("")
        for r in results:
            if r["issues"]:
                lines.append(f"#### `{r['id']}` - {r['name']}")
                for issue in r["issues"]:
                    lines.append(f"- [ ] {issue}")
                lines.append("")

    # 경고 있는 항목
    if with_warnings > 0:
        lines.append("### 경고 (검토 권장)")
        lines.append("")
        for r in results:
            if r["warnings"] and not r["issues"]:
                lines.append(f"#### `{r['id']}` - {r['name']}")
                for warning in r["warnings"]:
                    lines.append(f"- [ ] {warning}")
                lines.append("")

    # 유효한 항목
    lines.append("### 유효한 항목")
    lines.append("")
    valid_items = [r for r in results if r["valid"] and not r["warnings"]]
    if valid_items:
        for r in valid_items:
            lines.append(f"- [x] `{r['id']}` - {r['name']}")
    else:
        lines.append("_모든 항목에 이슈 또는 경고가 있습니다._")

    return "\n".join(lines)


def format_text(results: list) -> str:
    """텍스트 리포트 생성"""
    lines = []

    for r in results:
        status = "OK" if r["valid"] else "FAIL"
        warning_count = len(r["warnings"])

        line = f"[{status}] {r['id']}: {r['name']}"
        if warning_count > 0:
            line += f" ({warning_count} warnings)"
        lines.append(line)

        for issue in r["issues"]:
            lines.append(f"  ERROR: {issue}")
        for warning in r["warnings"]:
            lines.append(f"  WARN: {warning}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="permits.yaml 검증")
    parser.add_argument("--markdown", action="store_true", help="마크다운 리포트 출력")
    parser.add_argument("--json", action="store_true", help="JSON 형식 출력")
    args = parser.parse_args()

    # 데이터 로드
    permits_data = load_permits()
    if permits_data is None:
        sys.exit(2)

    law_index = load_law_index()
    checklists = get_available_checklists()

    print(f"검증 중: {len(permits_data.get('items', []))}개 항목", file=sys.stderr)
    print(f"참조 데이터: law_index {len(law_index)}개, checklists {len(checklists)}개", file=sys.stderr)

    # 검증 실행
    results = validate_all(permits_data, law_index, checklists)

    # 결과 출력
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    elif args.markdown:
        print(format_markdown(results, permits_data))
    else:
        print(format_text(results))

    # 종료 코드
    has_issues = any(r["issues"] for r in results)
    sys.exit(1 if has_issues else 0)


if __name__ == "__main__":
    main()
