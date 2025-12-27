#!/usr/bin/env python3
"""
법령 개정 감지 스크립트

law_index.yaml에 등록된 주요 법령들의 개정 여부를 확인하고,
영향받는 YAML 파일을 식별합니다.

Usage:
    python check_law_updates.py                    # 마지막 확인일 이후 개정 감지
    python check_law_updates.py --days 30          # 최근 30일간 개정 감지
    python check_law_updates.py --since 2025-01-01 # 특정 날짜 이후 개정 감지
    python check_law_updates.py --markdown         # GitHub Issue용 마크다운 출력
    python check_law_updates.py --update-state     # 마지막 확인일 업데이트

환경변수:
    BEOPSUNY_OC_CODE: law.go.kr API 인증 코드 (필수)
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple

import yaml

# 경로 설정
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent.parent
ASSETS_DIR = SKILL_DIR / "assets"
DATA_DIR = SKILL_DIR / "data"

# API 설정
API_BASE_URL = "http://www.law.go.kr/DRF"
ENV_OC_CODE = "BEOPSUNY_OC_CODE"

# 상태 파일 (마지막 확인일 저장)
STATE_FILE = DATA_DIR / "maintenance_state.json"

# 역 인덱스 파일
LAW_TO_FILES_PATH = DATA_DIR / "law_to_files.json"


def load_oc_code():
    """OC 코드 로드"""
    oc_code = os.environ.get(ENV_OC_CODE)
    if not oc_code:
        print(f"Error: {ENV_OC_CODE} 환경변수가 설정되지 않았습니다.", file=sys.stderr)
        print(f"export {ENV_OC_CODE}=your_oc_code", file=sys.stderr)
        sys.exit(1)
    return oc_code


def load_law_index():
    """law_index.yaml에서 주요 법령 목록 로드"""
    law_index_path = ASSETS_DIR / "law_index.yaml"
    if not law_index_path.exists():
        print(f"Error: {law_index_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(law_index_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return data.get("major_laws", {})


def load_reverse_index():
    """역 인덱스 로드 (없으면 생성)"""
    if not LAW_TO_FILES_PATH.exists():
        # 역 인덱스 생성 - 같은 디렉토리의 모듈 import
        try:
            from maintenance.build_law_index import build_reverse_index
        except ImportError:
            # 직접 실행 시 상대 경로로 시도
            sys.path.insert(0, str(SCRIPT_DIR))
            from build_law_index import build_reverse_index

        index = build_reverse_index()
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(LAW_TO_FILES_PATH, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
        return index

    with open(LAW_TO_FILES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_state():
    """상태 파일 로드"""
    if STATE_FILE.exists():
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state):
    """상태 파일 저장"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def api_request(endpoint: str, params: dict) -> Tuple[Optional[ET.Element], Optional[str]]:
    """law.go.kr API 호출

    Returns:
        (XML Element, None) on success
        (None, error_message) on failure
    """
    query = urllib.parse.urlencode(params)
    url = f"{API_BASE_URL}/{endpoint}?{query}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read().decode("utf-8")
            return ET.fromstring(content), None
    except urllib.error.HTTPError as e:
        error_msg = f"HTTP {e.code} {e.reason} for {endpoint}"
        print(f"API Error: {error_msg}", file=sys.stderr)
        return None, error_msg
    except urllib.error.URLError as e:
        error_msg = f"Connection failed: {e.reason} for {endpoint}"
        print(f"API Error: {error_msg}", file=sys.stderr)
        return None, error_msg
    except ET.ParseError as e:
        error_msg = f"XML parse error: {e} for {endpoint}"
        print(f"API Error: {error_msg}", file=sys.stderr)
        return None, error_msg
    except TimeoutError:
        error_msg = f"Timeout after 30s for {endpoint}"
        print(f"API Error: {error_msg}", file=sys.stderr)
        return None, error_msg


def get_law_info(law_id: str, oc_code: str) -> Optional[dict]:
    """법령 ID로 기본 정보 조회"""
    params = {
        "OC": oc_code,
        "target": "law",
        "type": "XML",
        "ID": law_id,
    }

    root, error = api_request("lawService.do", params)
    if root is None:
        return None

    return {
        "name": root.findtext(".//법령명_한글", "") or root.findtext(".//법령명", ""),
        "promul_date": root.findtext(".//공포일자", ""),
        "enforce_date": root.findtext(".//시행일자", ""),
        "revision_type": root.findtext(".//제개정구분명", ""),
    }


def get_recent_amendments(oc_code: str, from_date: str, to_date: str = None) -> Tuple[list, bool]:
    """최근 개정 법령 목록 조회

    Returns:
        (results_list, success_flag)
        - success=True: API 호출 성공 (빈 리스트도 성공)
        - success=False: API 호출 실패
    """
    if to_date is None:
        to_date = datetime.now().strftime("%Y%m%d")

    params = {
        "OC": oc_code,
        "target": "law",
        "type": "XML",
        "display": 100,
        "efYd": f"{from_date}~{to_date}",
        "sort": "efdes",
    }

    root, error = api_request("lawSearch.do", params)
    if root is None:
        return [], False  # API 실패

    results = []
    for item in root.findall(".//law"):
        results.append({
            "id": item.findtext("법령ID", ""),
            "name": item.findtext("법령명한글", "") or item.findtext("법령명", ""),
            "promul_date": item.findtext("공포일자", ""),
            "enforce_date": item.findtext("시행일자", ""),
            "revision_type": item.findtext("제개정구분명", ""),
        })

    return results, True  # API 성공


def check_amendments(since_date: str, major_laws: dict, reverse_index: dict, oc_code: str) -> Tuple[list, bool]:
    """개정된 법령 확인 및 영향 분석

    Returns:
        (affected_list, success_flag)
    """
    # 최근 개정 법령 조회
    recent, success = get_recent_amendments(oc_code, since_date)
    if not success:
        return [], False

    # 주요 법령 이름 목록
    major_law_names = set(major_laws.keys())

    # 영향받는 법령 필터링
    affected = []
    for law in recent:
        law_name = law["name"]

        # 주요 법령인지 확인 (부분 매칭)
        matched_name = None
        for name in major_law_names:
            if name in law_name or law_name in name:
                matched_name = name
                break

        if matched_name:
            # 영향받는 파일 조회
            files = []
            if matched_name in reverse_index:
                files = reverse_index[matched_name]["files"]

            affected.append({
                "law_name": law_name,
                "matched_name": matched_name,
                "promul_date": law["promul_date"],
                "enforce_date": law["enforce_date"],
                "revision_type": law["revision_type"],
                "affected_files": files,
            })

    return affected, True


def format_markdown(affected: list, since_date: str) -> str:
    """GitHub Issue용 마크다운 생성"""
    if not affected:
        return f"## ✅ 법령 개정 없음 ({since_date} 이후)\n\n주요 법령 중 개정된 항목이 없습니다."

    lines = [
        f"## 🔔 법령 개정 감지 ({since_date} 이후)",
        "",
        f"총 **{len(affected)}개** 법령이 개정되었습니다.",
        "",
        "### 개정된 법령",
        "",
    ]

    for item in affected:
        emoji = "🆕" if item["revision_type"] == "제정" else "📝"
        lines.append(f"#### {emoji} {item['law_name']}")
        lines.append(f"- **개정 유형**: {item['revision_type']}")
        lines.append(f"- **공포일**: {item['promul_date']}")
        lines.append(f"- **시행일**: {item['enforce_date']}")
        lines.append("")

        if item["affected_files"]:
            lines.append("**영향받는 파일:**")
            for file_info in item["affected_files"]:
                path = file_info["path"]
                items = file_info.get("items", [])
                if items:
                    item_str = ", ".join(items[:5])
                    if len(items) > 5:
                        item_str += f" 외 {len(items) - 5}개"
                    lines.append(f"- [ ] `{path}` ({item_str})")
                else:
                    lines.append(f"- [ ] `{path}`")
            lines.append("")

    lines.extend([
        "### 권장 조치",
        "",
        "1. 개정 내용 확인 ([법령정보센터](https://www.law.go.kr))",
        "2. 해당 YAML 파일 업데이트",
        "3. `last_updated` 필드 갱신",
        "4. PR 생성 후 머지",
        "",
        "---",
        f"*자동 생성: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
    ])

    return "\n".join(lines)


def format_text(affected: list, since_date: str) -> str:
    """터미널 출력용 텍스트 생성"""
    if not affected:
        return f"✅ 법령 개정 없음 ({since_date} 이후)"

    lines = [
        f"\n=== 법령 개정 감지 ({since_date} 이후) ===",
        f"총 {len(affected)}개 법령 개정",
        "",
    ]

    for item in affected:
        emoji = "🆕" if item["revision_type"] == "제정" else "📝"
        lines.append(f"{emoji} [{item['revision_type']}] {item['law_name']}")
        lines.append(f"   공포일: {item['promul_date']} | 시행일: {item['enforce_date']}")

        if item["affected_files"]:
            lines.append("   영향받는 파일:")
            for file_info in item["affected_files"]:
                path = file_info["path"]
                items = file_info.get("items", [])
                if items:
                    lines.append(f"     └─ {path} [{', '.join(items[:3])}{'...' if len(items) > 3 else ''}]")
                else:
                    lines.append(f"     └─ {path}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="법령 개정 감지")
    parser.add_argument("--days", type=int, help="최근 N일간 확인")
    parser.add_argument("--since", type=str, help="시작 날짜 (YYYY-MM-DD)")
    parser.add_argument("--markdown", action="store_true", help="GitHub Issue용 마크다운 출력")
    parser.add_argument("--update-state", action="store_true", help="마지막 확인일 업데이트")
    parser.add_argument("--json", action="store_true", help="JSON 형식으로 출력")
    args = parser.parse_args()

    # OC 코드 로드
    oc_code = load_oc_code()

    # 날짜 결정
    state = load_state()
    if args.since:
        since_date = args.since.replace("-", "")
    elif args.days:
        since_date = (datetime.now() - timedelta(days=args.days)).strftime("%Y%m%d")
    elif "last_check" in state:
        since_date = state["last_check"]
    else:
        # 기본: 30일 전
        since_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

    # 데이터 로드
    major_laws = load_law_index()
    reverse_index = load_reverse_index()

    # 개정 확인
    print(f"Checking amendments since {since_date}...", file=sys.stderr)
    affected, success = check_amendments(since_date, major_laws, reverse_index, oc_code)

    # API 실패 시 exit code 2
    if not success:
        print("Error: API 호출 실패. 나중에 다시 시도하세요.", file=sys.stderr)
        sys.exit(2)

    # 출력
    if args.json:
        output = {
            "since_date": since_date,
            "check_date": datetime.now().strftime("%Y%m%d"),
            "affected_count": len(affected),
            "affected": affected,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    elif args.markdown:
        print(format_markdown(affected, since_date))
    else:
        print(format_text(affected, since_date))

    # 상태 업데이트
    if args.update_state:
        state["last_check"] = datetime.now().strftime("%Y%m%d")
        save_state(state)
        print(f"\n✅ 마지막 확인일 업데이트: {state['last_check']}", file=sys.stderr)

    # 종료 코드: 개정된 법령이 있으면 1
    sys.exit(1 if affected else 0)


if __name__ == "__main__":
    main()
