#!/usr/bin/env python3
"""
Korean National Assembly Bill Fetcher - 열린국회정보 API 클라이언트

Usage:
    python fetch_bill.py search "검색어" [--age 22] [--save]
    python fetch_bill.py recent [--days 30] [--keyword "상법"] [--save]
    python fetch_bill.py track "법령명" [--save]
    python fetch_bill.py detail --bill-no 2214519
    python fetch_bill.py pending [--keyword "상법"] [--save]
    python fetch_bill.py votes --bill-no 2214519
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

import yaml

# 스크립트 위치 기준으로 경로 설정
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
CONFIG_PATH = SKILL_DIR / "config" / "settings.yaml"
DATA_DIR = SKILL_DIR / "data" / "bills"

# 열린국회정보 API 기본 URL (HTTPS는 400 에러 발생, HTTP 사용)
BASE_URL = "http://open.assembly.go.kr/portal/openapi"

# 환경변수 이름
ENV_ASSEMBLY_API_KEY = "BEOPSUNY_ASSEMBLY_API_KEY"

# 서비스 코드 매핑
SERVICE_CODES = {
    "bills": "nzmimeepazxkubdpn",       # 국회의원 발의법률안
    "all_bills": "ALLBILL",              # 의안정보 통합
    "pending": "nwbqublzajtcqpdae",      # 계류의안
    "processed": "nzpltgfqabtcpsmai",    # 처리의안
    "recent_plenary": "nxjuyqnxadtotdrbw",  # 최근 본회의처리 의안
    "votes": "ncocpgfiaoituanbr",        # 의안별 표결현황
    "bill_detail": "BILLINFODETAIL",     # 의안 상세정보
}

# 현재 국회 대수
CURRENT_AGE = 22


def is_exact_law_match(law_name: str, bill_name: str) -> bool:
    """
    법령명이 의안명에 정확히 매칭되는지 확인

    "상법"이 "국가배상법", "기상법", "손해배상법" 등과 구분되어야 함
    """
    import re

    # 의안명에서 법령명 부분 추출 (예: "상법 일부개정법률안" -> "상법")
    # 패턴: [법령명] + (일부|전부)개정법률안
    pattern = rf'^(.+?)\s*(일부|전부)?개정법률안'
    match = re.match(pattern, bill_name)

    if match:
        extracted_law = match.group(1).strip()
        # 정확히 일치하거나, 추출된 법령명이 검색 법령명으로 끝나는 경우
        # 예: "상법" == "상법" 또는 "상법 시행령" ends with "상법"은 안됨
        return extracted_law == law_name
    else:
        # 패턴 매칭 실패 시 단순 포함 확인 (fallback)
        return law_name in bill_name


def save_to_markdown(results: list, query_type: str, query_info: dict, filename: str = None) -> Path:
    """
    검색 결과를 frontmatter가 포함된 Markdown 파일로 저장

    Args:
        results: 검색 결과 리스트
        query_type: 검색 유형 (search, track, recent, pending)
        query_info: 검색 조건 정보
        filename: 저장할 파일명 (없으면 자동 생성)
    """
    now = datetime.now()

    # 파일명 생성
    if not filename:
        safe_query = "".join(c for c in query_info.get('query', 'results')
                           if c.isalnum() or c in (' ', '_', '-')).strip()
        filename = f"{query_type}_{safe_query}_{now.strftime('%Y%m%d_%H%M%S')}.md"

    filepath = DATA_DIR / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Frontmatter 생성
    frontmatter_lines = [
        "---",
        f"title: \"{query_info.get('title', '의안 검색 결과')}\"",
        f"type: 의안",
        f"query_type: \"{query_type}\"",
    ]

    if query_info.get('query'):
        frontmatter_lines.append(f"query: \"{query_info['query']}\"")
    if query_info.get('age'):
        frontmatter_lines.append(f"assembly_age: {query_info['age']}")
    if query_info.get('days'):
        frontmatter_lines.append(f"days_filter: {query_info['days']}")

    frontmatter_lines.extend([
        f"total_count: {len(results)}",
        f"source_name: \"열린국회정보\"",
        f"source_url: \"https://open.assembly.go.kr\"",
        f"retrieved_at: \"{now.strftime('%Y-%m-%d %H:%M:%S')}\"",
        f"tags: [\"의안\", \"국회\", \"{query_type}\"]",
        "---",
        "",
    ])

    # 본문 생성
    content_lines = [
        f"# {query_info.get('title', '의안 검색 결과')}",
        "",
        f"> 검색일시: {now.strftime('%Y-%m-%d %H:%M:%S')}",
        f"> 총 {len(results)}건",
        "",
    ]

    # 결과 테이블
    if results:
        content_lines.extend([
            "## 검색 결과",
            "",
            "| 의안번호 | 의안명 | 대표발의 | 발의일 | 상태 |",
            "|---------|-------|---------|-------|-----|",
        ])

        for r in results:
            bill_no = r.get('bill_no', '')
            bill_name = r.get('name', '')
            proposer = r.get('proposer', '')
            propose_date = r.get('propose_date', '')
            proc_result = r.get('proc_result', '') or '계류'
            bill_id = r.get('bill_id', '') or f"PRC_{bill_no}"
            link = f"[{bill_no}](https://likms.assembly.go.kr/bill/billDetail.do?billId={bill_id})"
            content_lines.append(f"| {link} | {bill_name} | {proposer} | {propose_date} | {proc_result} |")

        content_lines.extend(["", ""])

        # 상세 목록
        content_lines.append("## 상세 목록")
        content_lines.append("")

        for r in results:
            bill_no = r.get('bill_no', '')
            bill_name = r.get('name', '')
            proposer = r.get('proposer', '')
            propose_date = r.get('propose_date', '')
            proc_result = r.get('proc_result', '') or '계류'
            committee = r.get('committee', '')
            bill_id = r.get('bill_id', '') or f"PRC_{bill_no}"

            content_lines.append(f"### [{bill_no}] {bill_name}")
            content_lines.append("")
            content_lines.append(f"- **대표발의**: {proposer}")
            content_lines.append(f"- **발의일**: {propose_date}")
            content_lines.append(f"- **처리상태**: {proc_result}")
            if committee:
                content_lines.append(f"- **소관위원회**: {committee}")
            content_lines.append(f"- **링크**: https://likms.assembly.go.kr/bill/billDetail.do?billId={bill_id}")
            content_lines.append("")

    # 파일 저장
    full_content = '\n'.join(frontmatter_lines) + '\n'.join(content_lines)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(full_content)

    print(f"\n📄 저장됨: {filepath}")
    return filepath


def load_config():
    """API 키 로드 (환경변수 > 설정파일)"""
    # 1. 환경변수 우선
    api_key = os.environ.get(ENV_ASSEMBLY_API_KEY)
    if api_key:
        return api_key

    # 2. 설정 파일 fallback
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
        api_key = config.get('assembly_api_key', '')
        if api_key:
            return api_key

    # API 키 없음
    print(f"Error: Assembly API key not found.", file=sys.stderr)
    print(f"", file=sys.stderr)
    print(f"Set one of the following:", file=sys.stderr)
    print(f"  1. Environment variable: export {ENV_ASSEMBLY_API_KEY}=your_api_key", file=sys.stderr)
    print(f"  2. Config file: {CONFIG_PATH}", file=sys.stderr)
    print(f"", file=sys.stderr)
    print(f"Get your API key at: https://open.assembly.go.kr", file=sys.stderr)
    sys.exit(1)


def api_request(service_code: str, params: dict, response_type: str = "json") -> dict:
    """열린국회정보 API 요청"""
    api_key = load_config()

    # 기본 파라미터
    base_params = {
        "KEY": api_key,
        "Type": response_type,
        "pIndex": params.get("pIndex", 1),
        "pSize": params.get("pSize", 100),
    }

    # 추가 파라미터 병합
    for key, value in params.items():
        if key not in ["pIndex", "pSize"] and value is not None:
            base_params[key] = value

    url = f"{BASE_URL}/{service_code}?{urllib.parse.urlencode(base_params)}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read().decode('utf-8')

            # HTML 응답 감지 (API 오류 시 HTML 반환됨)
            if content.strip().startswith('<!DOCTYPE') or content.strip().startswith('<html'):
                print(f"Error: API returned HTML instead of JSON.", file=sys.stderr)
                print(f"This usually means the domain is not in the network allowlist.", file=sys.stderr)
                print(f"", file=sys.stderr)
                print(f"Solution: Add 'open.assembly.go.kr' to allowed domains in:", file=sys.stderr)
                print(f"  Claude Desktop: Settings > Capabilities > Network egress", file=sys.stderr)
                print(f"", file=sys.stderr)
                print(f"URL: {url}", file=sys.stderr)
                sys.exit(1)

            return json.loads(content)
    except urllib.error.HTTPError as e:
        print(f"Error: HTTP {e.code} - {e.reason}", file=sys.stderr)
        if e.code == 403:
            print(f"", file=sys.stderr)
            print(f"403 Forbidden usually means network access is blocked.", file=sys.stderr)
            print(f"Add 'open.assembly.go.kr' to allowed domains in:", file=sys.stderr)
            print(f"  Claude Desktop: Settings > Capabilities > Network egress", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: API request failed - {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse JSON response - {e}", file=sys.stderr)
        print(f"", file=sys.stderr)
        print(f"This may indicate the API returned an error page instead of JSON.", file=sys.stderr)
        print(f"Check if 'open.assembly.go.kr' is in the allowed domains list.", file=sys.stderr)
        print(f"URL: {url}", file=sys.stderr)
        sys.exit(1)


def search_bills(query: str, age: int = CURRENT_AGE, proc_result: str = None,
                 display: int = 20, page: int = 1):
    """
    국회의원 발의법률안 검색

    Args:
        query: 검색어 (법률안명)
        age: 국회 대수 (기본: 22대)
        proc_result: 처리상태 필터
        display: 결과 개수
        page: 페이지 번호
    """
    params = {
        "AGE": age,
        "BILL_NAME": query,
        "pIndex": page,
        "pSize": display,
    }

    if proc_result:
        params["PROC_RESULT"] = proc_result

    data = api_request(SERVICE_CODES["bills"], params)

    # 결과 파싱
    service_key = SERVICE_CODES["bills"]
    if service_key not in data:
        print(f"\n=== 의안 검색 결과: '{query}' (0건) ===\n")
        print("검색 결과가 없습니다.")
        return []

    result_data = data[service_key]

    # 헤더 정보 확인
    head = result_data[0].get("head", [{}])
    total = 0
    for h in head:
        if "list_total_count" in h:
            total = h["list_total_count"]
            break

    print(f"\n=== 의안 검색 결과: '{query}' ({age}대 국회, 총 {total}건) ===\n")

    # 실제 데이터는 두 번째 요소에 있음
    if len(result_data) < 2 or "row" not in result_data[1]:
        print("검색 결과가 없습니다.")
        return []

    rows = result_data[1]["row"]
    results = []

    for item in rows:
        bill_id = item.get("BILL_ID", "")
        bill_no = item.get("BILL_NO", "")
        bill_name = item.get("BILL_NAME", "")
        proposer = item.get("RST_PROPOSER", "") or item.get("PROPOSER", "")
        propose_dt = item.get("PROPOSE_DT", "")
        proc_result_text = item.get("PROC_RESULT", "")
        committee = item.get("CURR_COMMITTEE", "") or item.get("COMMITTEE", "")

        results.append({
            "bill_id": bill_id,
            "bill_no": bill_no,
            "name": bill_name,
            "proposer": proposer,
            "propose_date": propose_dt,
            "proc_result": proc_result_text,
            "committee": committee,
        })

        # 상태 이모지
        status_emoji = "📋"
        if proc_result_text == "원안가결" or proc_result_text == "수정가결":
            status_emoji = "✅"
        elif not proc_result_text or proc_result_text == "계류":
            status_emoji = "⏳"
        elif proc_result_text and ("폐기" in proc_result_text or "철회" in proc_result_text):
            status_emoji = "❌"

        print(f"{status_emoji} [{bill_no}] {bill_name}")
        print(f"   대표발의: {proposer}")
        print(f"   발의일: {propose_dt} | 상태: {proc_result_text or '계류'}")
        if committee:
            print(f"   소관위: {committee}")
        # BILL_ID가 있으면 사용, 없으면 PRC_의안번호 형식
        link_id = bill_id if bill_id else f"PRC_{bill_no}"
        print(f"   링크: https://likms.assembly.go.kr/bill/billDetail.do?billId={link_id}")
        print()

    print(f"표시: {len(results)}건 / 전체: {total}건")
    return results


def get_recent_bills(days: int = 30, keyword: str = None, age: int = CURRENT_AGE,
                     display: int = 50):
    """
    최근 발의된 법률안 조회

    Args:
        days: 최근 N일
        keyword: 법률안명 필터 키워드
        age: 국회 대수
        display: 결과 개수
    """
    params = {
        "AGE": age,
        "pSize": display,
    }

    data = api_request(SERVICE_CODES["bills"], params)

    service_key = SERVICE_CODES["bills"]
    if service_key not in data:
        print(f"\n=== 최근 발의 법률안 (0건) ===\n")
        return []

    result_data = data[service_key]

    # 날짜 필터 계산
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    if len(result_data) < 2 or "row" not in result_data[1]:
        print("검색 결과가 없습니다.")
        return []

    rows = result_data[1]["row"]
    results = []

    print(f"\n=== 최근 {days}일 발의 법률안 ({age}대 국회) ===\n")

    for item in rows:
        propose_dt = item.get("PROPOSE_DT", "")

        # 날짜 필터링
        if propose_dt and propose_dt < cutoff_date:
            continue

        bill_no = item.get("BILL_NO", "")
        bill_name = item.get("BILL_NAME", "")
        proposer = item.get("RST_PROPOSER", "") or item.get("PROPOSER", "")
        proc_result_text = item.get("PROC_RESULT", "")

        # 키워드 필터링
        if keyword and keyword not in bill_name:
            continue

        results.append({
            "bill_no": bill_no,
            "name": bill_name,
            "proposer": proposer,
            "propose_date": propose_dt,
            "proc_result": proc_result_text,
        })

        print(f"📝 [{bill_no}] {bill_name}")
        print(f"   대표발의: {proposer} | 발의일: {propose_dt}")
        print()

    print(f"총 {len(results)}건")
    return results


def get_pending_bills(keyword: str = None, age: int = CURRENT_AGE, display: int = 50):
    """
    계류 중인 의안 조회

    Args:
        keyword: 의안명 필터 키워드
        age: 국회 대수
        display: 결과 개수
    """
    params = {
        "AGE": age,
        "pSize": display,
    }

    if keyword:
        params["BILL_NAME"] = keyword

    data = api_request(SERVICE_CODES["pending"], params)

    service_key = SERVICE_CODES["pending"]
    if service_key not in data:
        print(f"\n=== 계류 의안 (0건) ===\n")
        return []

    result_data = data[service_key]

    # 헤더에서 총 건수 추출
    head = result_data[0].get("head", [{}])
    total = 0
    for h in head:
        if "list_total_count" in h:
            total = h["list_total_count"]
            break

    keyword_str = f" - '{keyword}'" if keyword else ""
    print(f"\n=== 계류 의안{keyword_str} ({age}대 국회, 총 {total}건) ===\n")

    if len(result_data) < 2 or "row" not in result_data[1]:
        print("검색 결과가 없습니다.")
        return []

    rows = result_data[1]["row"]
    results = []

    for item in rows:
        bill_no = item.get("BILL_NO", "")
        bill_name = item.get("BILL_NAME", "")
        proposer = item.get("PROPOSER", "")
        propose_dt = item.get("PROPOSE_DT", "")
        committee = item.get("CURR_COMMITTEE", "") or item.get("COMMITTEE", "")

        results.append({
            "bill_no": bill_no,
            "name": bill_name,
            "proposer": proposer,
            "propose_date": propose_dt,
            "committee": committee,
        })

        print(f"⏳ [{bill_no}] {bill_name}")
        print(f"   제안자: {proposer}")
        print(f"   발의일: {propose_dt}")
        if committee:
            print(f"   소관위: {committee}")
        print()

    print(f"표시: {len(results)}건 / 전체: {total}건")
    return results


def track_law_bills(law_name: str, age: int = CURRENT_AGE):
    """
    특정 법령 관련 개정안 추적

    Args:
        law_name: 추적할 법령명 (예: "상법", "민법")
        age: 국회 대수
    """
    print(f"\n=== '{law_name}' 관련 의안 추적 ({age}대 국회) ===\n")

    # 1. 해당 법령 개정안 검색
    search_terms = [
        f"{law_name} 일부개정법률안",
        f"{law_name} 전부개정법률안",
        law_name,
    ]

    all_results = []
    seen_bill_nos = set()

    for term in search_terms:
        params = {
            "AGE": age,
            "BILL_NAME": term,
            "pSize": 100,
        }

        data = api_request(SERVICE_CODES["bills"], params)
        service_key = SERVICE_CODES["bills"]

        if service_key not in data:
            continue

        result_data = data[service_key]
        if len(result_data) < 2 or "row" not in result_data[1]:
            continue

        rows = result_data[1]["row"]

        for item in rows:
            bill_no = item.get("BILL_NO", "")
            bill_name = item.get("BILL_NAME", "")

            # 정확히 해당 법령 개정안인지 확인
            # "상법"은 "국가배상법", "기상법"과 구분해야 함
            if not is_exact_law_match(law_name, bill_name):
                continue

            # 중복 제거
            if bill_no in seen_bill_nos:
                continue
            seen_bill_nos.add(bill_no)

            bill_id = item.get("BILL_ID", "")
            proposer = item.get("RST_PROPOSER", "") or item.get("PROPOSER", "")
            propose_dt = item.get("PROPOSE_DT", "")
            proc_result = item.get("PROC_RESULT", "")
            committee = item.get("CURR_COMMITTEE", "") or item.get("COMMITTEE", "")

            all_results.append({
                "bill_id": bill_id,
                "bill_no": bill_no,
                "name": bill_name,
                "proposer": proposer,
                "propose_date": propose_dt,
                "proc_result": proc_result,
                "committee": committee,
            })

    # 발의일 기준 정렬 (최신순)
    all_results.sort(key=lambda x: x["propose_date"], reverse=True)

    if not all_results:
        print(f"'{law_name}' 관련 발의된 의안이 없습니다.")
        return []

    # 상태별 분류
    pending = [r for r in all_results if not r["proc_result"] or r["proc_result"] == "계류"]
    passed = [r for r in all_results if r["proc_result"] in ["원안가결", "수정가결"]]
    others = [r for r in all_results if r not in pending and r not in passed]

    print(f"📊 총 {len(all_results)}건 발견\n")
    print(f"   ⏳ 계류: {len(pending)}건")
    print(f"   ✅ 가결: {len(passed)}건")
    print(f"   📋 기타: {len(others)}건")
    print()

    # 계류 중인 의안 출력
    if pending:
        print("─" * 50)
        print("⏳ 계류 중인 의안:")
        print("─" * 50)
        for r in pending:
            print(f"\n📋 [{r['bill_no']}] {r['name']}")
            print(f"   대표발의: {r['proposer']}")
            print(f"   발의일: {r['propose_date']}")
            if r['committee']:
                print(f"   소관위: {r['committee']}")
            link_id = r.get('bill_id') or f"PRC_{r['bill_no']}"
            print(f"   링크: https://likms.assembly.go.kr/bill/billDetail.do?billId={link_id}")

    # 가결된 의안 출력
    if passed:
        print()
        print("─" * 50)
        print("✅ 가결된 의안:")
        print("─" * 50)
        for r in passed:
            print(f"\n✅ [{r['bill_no']}] {r['name']}")
            print(f"   대표발의: {r['proposer']}")
            print(f"   발의일: {r['propose_date']} | 결과: {r['proc_result']}")

    return all_results


def get_bill_votes(bill_no: str, age: int = CURRENT_AGE):
    """
    의안별 표결현황 조회

    Args:
        bill_no: 의안번호
        age: 국회 대수
    """
    params = {
        "AGE": age,
        "BILL_NO": bill_no,
        "pSize": 10,
    }

    data = api_request(SERVICE_CODES["votes"], params)

    service_key = SERVICE_CODES["votes"]
    if service_key not in data:
        print(f"\n=== 의안 표결현황: {bill_no} ===\n")
        print("표결 정보가 없습니다.")
        return None

    result_data = data[service_key]

    if len(result_data) < 2 or "row" not in result_data[1]:
        print("표결 정보가 없습니다.")
        return None

    rows = result_data[1]["row"]

    print(f"\n=== 의안 표결현황: {bill_no} ===\n")

    for item in rows:
        bill_name = item.get("BILL_NAME", "")
        vote_date = item.get("VOTE_DATE", "")
        yes_count = item.get("YES_TCNT", 0)
        no_count = item.get("NO_TCNT", 0)
        abstain_count = item.get("BLANK_TCNT", 0)
        result = item.get("RESULT", "")

        print(f"📜 {bill_name}")
        print(f"   표결일: {vote_date}")
        print(f"   찬성: {yes_count} | 반대: {no_count} | 기권: {abstain_count}")
        print(f"   결과: {result}")
        print()

        return {
            "bill_no": bill_no,
            "name": bill_name,
            "vote_date": vote_date,
            "yes": yes_count,
            "no": no_count,
            "abstain": abstain_count,
            "result": result,
        }

    return None


def main():
    parser = argparse.ArgumentParser(description='Korean National Assembly Bill Fetcher')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # search 명령
    search_parser = subparsers.add_parser('search', help='의안 검색')
    search_parser.add_argument('query', help='검색어 (법률안명)')
    search_parser.add_argument('--age', type=int, default=CURRENT_AGE,
                               help=f'국회 대수 (기본: {CURRENT_AGE}대)')
    search_parser.add_argument('--status', help='처리상태 필터')
    search_parser.add_argument('--display', type=int, default=20, help='결과 개수')
    search_parser.add_argument('--page', type=int, default=1, help='페이지 번호')
    search_parser.add_argument('--save', action='store_true', help='결과를 Markdown으로 저장')

    # recent 명령
    recent_parser = subparsers.add_parser('recent', help='최근 발의 법률안')
    recent_parser.add_argument('--days', type=int, default=30, help='최근 N일')
    recent_parser.add_argument('--keyword', help='법률안명 키워드 필터')
    recent_parser.add_argument('--age', type=int, default=CURRENT_AGE, help='국회 대수')
    recent_parser.add_argument('--display', type=int, default=50, help='결과 개수')
    recent_parser.add_argument('--save', action='store_true', help='결과를 Markdown으로 저장')

    # pending 명령
    pending_parser = subparsers.add_parser('pending', help='계류 의안 조회')
    pending_parser.add_argument('--keyword', help='의안명 키워드 필터')
    pending_parser.add_argument('--age', type=int, default=CURRENT_AGE, help='국회 대수')
    pending_parser.add_argument('--display', type=int, default=50, help='결과 개수')
    pending_parser.add_argument('--save', action='store_true', help='결과를 Markdown으로 저장')

    # track 명령
    track_parser = subparsers.add_parser('track', help='특정 법령 개정안 추적')
    track_parser.add_argument('law_name', help='추적할 법령명 (예: 상법, 민법)')
    track_parser.add_argument('--age', type=int, default=CURRENT_AGE, help='국회 대수')
    track_parser.add_argument('--save', action='store_true', help='결과를 Markdown으로 저장')

    # votes 명령
    votes_parser = subparsers.add_parser('votes', help='의안 표결현황')
    votes_parser.add_argument('--bill-no', required=True, help='의안번호')
    votes_parser.add_argument('--age', type=int, default=CURRENT_AGE, help='국회 대수')

    args = parser.parse_args()

    if args.command == 'search':
        results = search_bills(args.query, args.age, args.status, args.display, args.page)
        if args.save and results:
            save_to_markdown(results, 'search', {
                'title': f"의안 검색: {args.query}",
                'query': args.query,
                'age': args.age,
            })
    elif args.command == 'recent':
        results = get_recent_bills(args.days, args.keyword, args.age, args.display)
        if args.save and results:
            keyword_str = f" - {args.keyword}" if args.keyword else ""
            save_to_markdown(results, 'recent', {
                'title': f"최근 {args.days}일 발의 법률안{keyword_str}",
                'query': args.keyword or '',
                'age': args.age,
                'days': args.days,
            })
    elif args.command == 'pending':
        results = get_pending_bills(args.keyword, args.age, args.display)
        if args.save and results:
            keyword_str = f" - {args.keyword}" if args.keyword else ""
            save_to_markdown(results, 'pending', {
                'title': f"계류 의안{keyword_str}",
                'query': args.keyword or '',
                'age': args.age,
            })
    elif args.command == 'track':
        results = track_law_bills(args.law_name, args.age)
        if args.save and results:
            save_to_markdown(results, 'track', {
                'title': f"{args.law_name} 관련 의안 추적",
                'query': args.law_name,
                'age': args.age,
            })
    elif args.command == 'votes':
        get_bill_votes(args.bill_no, args.age)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
