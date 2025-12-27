#!/usr/bin/env python3
"""
조문 검증 스크립트

YAML 파일에 인용된 법조문이 실제로 존재하는지 검증합니다.
분기별 실행 권장 (API 호출 제한 고려).

Usage:
    python validate_citations.py              # 전체 검증 (dry-run)
    python validate_citations.py --sample 10  # 랜덤 10개만 검증
    python validate_citations.py --law "상법" # 특정 법령만 검증
    python validate_citations.py --markdown   # 마크다운 리포트 출력

환경변수:
    BEOPSUNY_OC_CODE: law.go.kr API 인증 코드 (필수)
"""

import argparse
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Tuple

import yaml

# 경로 설정
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent.parent
ASSETS_DIR = SKILL_DIR / "assets"
CHECKLISTS_DIR = ASSETS_DIR / "checklists"

# API 설정
API_BASE_URL = "http://www.law.go.kr/DRF"
ENV_OC_CODE = "BEOPSUNY_OC_CODE"

# 조문 참조 패턴: "법령명 제XX조", "법령명 제XX조의2 제3항"
ARTICLE_PATTERN = re.compile(
    r"([가-힣]+(?:법|령|규칙|규정))\s*제(\d+)조(?:의(\d+))?(?:\s*제(\d+)항)?"
)


def load_oc_code():
    """OC 코드 로드"""
    oc_code = os.environ.get(ENV_OC_CODE)
    if not oc_code:
        print(f"Error: {ENV_OC_CODE} 환경변수가 설정되지 않았습니다.", file=sys.stderr)
        sys.exit(1)
    return oc_code


def load_law_index():
    """law_index.yaml에서 법령 ID 매핑 로드"""
    law_index_path = ASSETS_DIR / "law_index.yaml"
    if not law_index_path.exists():
        return {}

    with open(law_index_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return data.get("major_laws", {})


def extract_citations_from_yaml(filepath: Path) -> list:
    """YAML 파일에서 조문 인용 추출"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        data = yaml.safe_load(content) or {}

    citations = []

    # 정규식으로 모든 조문 참조 추출
    for match in ARTICLE_PATTERN.finditer(content):
        law_name = match.group(1)
        article_num = match.group(2)
        article_sub = match.group(3)  # 조의X
        paragraph = match.group(4)  # 제X항

        citation = {
            "law_name": law_name,
            "article": f"제{article_num}조" + (f"의{article_sub}" if article_sub else ""),
            "paragraph": f"제{paragraph}항" if paragraph else None,
            "full_text": match.group(0),
            "file": str(filepath.relative_to(ASSETS_DIR)),
        }
        citations.append(citation)

    return citations


def collect_all_citations() -> list:
    """모든 YAML 파일에서 조문 인용 수집"""
    yaml_files = [
        ASSETS_DIR / "compliance_calendar.yaml",
        ASSETS_DIR / "clause_references.yaml",
    ]
    yaml_files.extend(CHECKLISTS_DIR.glob("*.yaml"))

    all_citations = []
    for filepath in yaml_files:
        if filepath.exists():
            citations = extract_citations_from_yaml(filepath)
            all_citations.extend(citations)

    return all_citations


def deduplicate_citations(citations: list) -> list:
    """중복 제거 (법령+조문 기준)"""
    seen = set()
    unique = []

    for c in citations:
        key = (c["law_name"], c["article"])
        if key not in seen:
            seen.add(key)
            unique.append(c)

    return unique


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
        error_msg = f"HTTP {e.code} {e.reason}"
        print(f"API Error: {error_msg}", file=sys.stderr)
        return None, error_msg
    except urllib.error.URLError as e:
        error_msg = f"Connection failed: {e.reason}"
        print(f"API Error: {error_msg}", file=sys.stderr)
        return None, error_msg
    except ET.ParseError as e:
        error_msg = f"XML parse error: {e}"
        print(f"API Error: {error_msg}", file=sys.stderr)
        return None, error_msg
    except TimeoutError:
        error_msg = "Timeout after 30s"
        print(f"API Error: {error_msg}", file=sys.stderr)
        return None, error_msg


def validate_citation(law_name: str, law_id: str, article: str, oc_code: str) -> dict:
    """조문 존재 여부 검증"""
    params = {
        "OC": oc_code,
        "target": "law",
        "type": "XML",
        "ID": law_id,
    }

    root, error = api_request("lawService.do", params)
    if root is None:
        return {"valid": None, "error": error or "API 호출 실패"}

    # 조문 번호 추출 (예: "제750조" → "750")
    article_match = re.match(r"제(\d+)조(?:의(\d+))?", article)
    if not article_match:
        return {"valid": None, "error": "조문 번호 파싱 실패"}

    target_num = article_match.group(1)
    target_sub = article_match.group(2)

    # 조문 검색
    for jo in root.findall(".//조문"):
        jo_num = jo.findtext("조문번호", "")
        jo_content = jo.findtext("조문내용", "")

        # 조문번호 매칭
        if target_sub:
            # 제X조의Y 형태
            if f"{target_num}조의{target_sub}" in jo_num or jo_num == f"{target_num}의{target_sub}":
                return {"valid": True, "jo_content": jo_content[:100]}
        else:
            # 제X조 형태
            if jo_num == target_num or jo_num.startswith(f"{target_num}조"):
                return {"valid": True, "jo_content": jo_content[:100]}

    # 조문 목록이 없는 경우 (API 응답 구조가 다를 수 있음)
    # 조/항 단위 조회가 안 되면 법령 존재만 확인
    law_name_found = root.findtext(".//법령명_한글", "") or root.findtext(".//법령명", "")
    if law_name_found:
        return {"valid": None, "error": "조문 단위 검증 불가 (법령은 존재)"}

    return {"valid": False, "error": "조문을 찾을 수 없음"}


def validate_citations(citations: list, law_index: dict, oc_code: str, delay: float = 0.5) -> list:
    """조문 목록 검증"""
    results = []

    for i, c in enumerate(citations):
        law_name = c["law_name"]

        # 법령 ID 조회
        law_id = law_index.get(law_name)
        if not law_id:
            results.append({
                **c,
                "valid": None,
                "error": "law_index.yaml에 없는 법령",
            })
            continue

        # API로 검증
        result = validate_citation(law_name, law_id, c["article"], oc_code)
        results.append({**c, **result})

        # API 호출 제한 방지
        if i < len(citations) - 1:
            time.sleep(delay)

        # 진행 상황 출력
        print(f"\r검증 중: {i + 1}/{len(citations)}", end="", file=sys.stderr)

    print("", file=sys.stderr)
    return results


def format_markdown(results: list) -> str:
    """마크다운 리포트 생성"""
    invalid = [r for r in results if r.get("valid") is False]
    unknown = [r for r in results if r.get("valid") is None]
    valid = [r for r in results if r.get("valid") is True]

    lines = [
        "## 📋 조문 검증 리포트",
        "",
        f"- ✅ 유효: {len(valid)}개",
        f"- ❓ 확인 필요: {len(unknown)}개",
        f"- ❌ 무효: {len(invalid)}개",
        "",
    ]

    if invalid:
        lines.append("### ❌ 무효 조문 (삭제/이동됨)")
        lines.append("")
        for r in invalid:
            lines.append(f"- `{r['file']}`: {r['full_text']}")
            lines.append(f"  - 오류: {r.get('error', 'N/A')}")
        lines.append("")

    if unknown:
        lines.append("### ❓ 확인 필요")
        lines.append("")
        for r in unknown:
            lines.append(f"- `{r['file']}`: {r['full_text']}")
            lines.append(f"  - 사유: {r.get('error', 'N/A')}")
        lines.append("")

    lines.extend([
        "---",
        f"*검증일: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}*",
    ])

    return "\n".join(lines)


def format_text(results: list) -> str:
    """터미널 출력용 텍스트"""
    invalid = [r for r in results if r.get("valid") is False]
    unknown = [r for r in results if r.get("valid") is None]
    valid = [r for r in results if r.get("valid") is True]

    lines = [
        "",
        "=== 조문 검증 결과 ===",
        "",
        f"✅ 유효: {len(valid)}개",
        f"❓ 확인 필요: {len(unknown)}개",
        f"❌ 무효: {len(invalid)}개",
        "",
    ]

    if invalid:
        lines.append("❌ 무효 조문:")
        for r in invalid:
            lines.append(f"   {r['full_text']} ({r['file']})")
        lines.append("")

    if unknown:
        lines.append("❓ 확인 필요:")
        for r in unknown[:10]:  # 상위 10개만
            lines.append(f"   {r['full_text']} - {r.get('error', '')}")
        if len(unknown) > 10:
            lines.append(f"   ... 외 {len(unknown) - 10}개")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="조문 검증")
    parser.add_argument("--sample", type=int, help="랜덤 N개만 검증")
    parser.add_argument("--law", type=str, help="특정 법령만 검증")
    parser.add_argument("--markdown", action="store_true", help="마크다운 출력")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    parser.add_argument("--dry-run", action="store_true", help="API 호출 없이 수집만")
    args = parser.parse_args()

    # 조문 수집
    print("조문 수집 중...", file=sys.stderr)
    citations = collect_all_citations()
    citations = deduplicate_citations(citations)

    # 필터링
    if args.law:
        citations = [c for c in citations if args.law in c["law_name"]]

    if args.sample and args.sample < len(citations):
        citations = random.sample(citations, args.sample)

    print(f"총 {len(citations)}개 조문 발견", file=sys.stderr)

    if args.dry_run:
        # API 호출 없이 수집 결과만 출력
        if args.json:
            print(json.dumps(citations, ensure_ascii=False, indent=2))
        else:
            for c in citations[:20]:
                print(f"  {c['law_name']} {c['article']} ({c['file']})")
            if len(citations) > 20:
                print(f"  ... 외 {len(citations) - 20}개")
        return

    # OC 코드 로드
    oc_code = load_oc_code()
    law_index = load_law_index()

    # 검증 실행
    results = validate_citations(citations, law_index, oc_code)

    # 출력
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    elif args.markdown:
        print(format_markdown(results))
    else:
        print(format_text(results))

    # 종료 코드: 무효 조문이 있으면 1
    invalid_count = len([r for r in results if r.get("valid") is False])
    sys.exit(1 if invalid_count > 0 else 0)


if __name__ == "__main__":
    main()
