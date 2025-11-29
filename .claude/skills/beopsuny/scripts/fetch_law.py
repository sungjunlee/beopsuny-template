#!/usr/bin/env python3
"""
Korean Law Fetcher - 국가법령정보센터 API 클라이언트

Usage:
    python fetch_law.py search "검색어" [--type law|prec|ordin|admrul|expc|detc]
    python fetch_law.py cases "검색어" [--court 대법원|고등|지방] [--from YYYYMMDD]
    python fetch_law.py fetch --id 법령ID [--with-decree]
    python fetch_law.py fetch --name "법령명" [--with-decree]
    python fetch_law.py recent [--days 30] [--from YYYYMMDD] [--to YYYYMMDD]
"""

import argparse
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

import yaml

# 스크립트 위치 기준으로 경로 설정
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
CONFIG_PATH = SKILL_DIR / "config" / "settings.yaml"
DATA_RAW_DIR = SKILL_DIR / "data" / "raw"
DATA_PARSED_DIR = SKILL_DIR / "data" / "parsed"

# API 기본 URL
BASE_URL = "http://www.law.go.kr/DRF"


def load_config():
    """설정 파일에서 OC 코드 로드"""
    if not CONFIG_PATH.exists():
        print(f"Error: Config file not found at {CONFIG_PATH}", file=sys.stderr)
        print("Please create config/settings.yaml with your OC code.", file=sys.stderr)
        sys.exit(1)

    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    return config.get('oc_code', '')


def api_request(endpoint: str, params: dict) -> ET.Element:
    """API 요청 및 XML 파싱"""
    url = f"{BASE_URL}/{endpoint}?{urllib.parse.urlencode(params)}"

    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            content = response.read().decode('utf-8')
            return ET.fromstring(content)
    except urllib.error.URLError as e:
        print(f"Error: API request failed - {e}", file=sys.stderr)
        sys.exit(1)
    except ET.ParseError as e:
        print(f"Error: Failed to parse XML response - {e}", file=sys.stderr)
        sys.exit(1)


def search_laws(query: str, target: str = "law", display: int = 20, page: int = 1, sort: str = None):
    """
    법령 검색

    Args:
        query: 검색어
        target: 검색 대상 (law: 법령, prec: 판례, ordin: 자치법규, admrul: 행정규칙, expc: 법령해석례, detc: 헌재결정례)
        display: 결과 개수 (최대 100)
        page: 페이지 번호
        sort: 정렬 기준 (date: 날짜순, name: 이름순)
    """
    oc = load_config()

    params = {
        'OC': oc,
        'target': target,
        'type': 'XML',
        'query': query,
        'display': display,
        'page': page,
    }

    if sort:
        params['sort'] = sort

    root = api_request('lawSearch.do', params)

    # 결과 파싱 - target에 따라 다른 태그 사용
    total = root.findtext('.//totalCnt', '0')

    target_names = {
        'law': '법령', 'prec': '판례', 'ordin': '자치법규',
        'admrul': '행정규칙', 'expc': '법령해석례', 'detc': '헌재결정례'
    }
    target_name = target_names.get(target, target)
    print(f"\n=== {target_name} 검색 결과: '{query}' (총 {total}건) ===\n")

    results = []

    # 판례 검색
    if target == 'prec':
        for item in root.findall('.//prec'):
            case_id = item.findtext('판례일련번호', '')
            case_name = item.findtext('사건명', '')
            case_number = item.findtext('사건번호', '')
            court_name = item.findtext('법원명', '')
            judge_date = item.findtext('선고일자', '')
            case_type = item.findtext('사건종류명', '')

            results.append({
                'id': case_id,
                'name': case_name,
                'case_number': case_number,
                'court': court_name,
                'judge_date': judge_date,
                'type': case_type,
            })

            print(f"⚖️  {case_name}")
            print(f"   사건번호: {case_number}")
            print(f"   법원: {court_name} | 선고일: {judge_date}")
            print(f"   사건종류: {case_type}")
            print(f"   링크: https://www.law.go.kr/판례/({case_number.replace(' ', '')})")
            print()

    # 행정규칙 검색
    elif target == 'admrul':
        for item in root.findall('.//admrul'):
            admrul_id = item.findtext('행정규칙일련번호', '')
            admrul_name = item.findtext('행정규칙명', '')
            admrul_type = item.findtext('행정규칙종류', '')
            promul_date = item.findtext('발령일자', '')
            enforce_date = item.findtext('시행일자', '')
            ministry = item.findtext('소관부처명', '')

            results.append({
                'id': admrul_id,
                'name': admrul_name,
                'type': admrul_type,
                'promul_date': promul_date,
                'enforce_date': enforce_date,
                'ministry': ministry,
            })

            print(f"📋 [{admrul_type}] {admrul_name}")
            print(f"   ID: {admrul_id}")
            print(f"   소관: {ministry}")
            print(f"   발령일: {promul_date} | 시행일: {enforce_date}")
            print(f"   링크: https://www.law.go.kr/행정규칙/{urllib.parse.quote(admrul_name)}")
            print()

    # 자치법규 검색
    elif target == 'ordin':
        for item in root.findall('.//law'):
            ordin_id = item.findtext('자치법규일련번호', '') or item.findtext('자치법규ID', '')
            ordin_name = item.findtext('자치법규명', '')
            ordin_type = item.findtext('자치법규종류', '')
            local_gov = item.findtext('지자체기관명', '')
            promul_date = item.findtext('공포일자', '')
            enforce_date = item.findtext('시행일자', '')

            results.append({
                'id': ordin_id,
                'name': ordin_name,
                'type': ordin_type,
                'local_gov': local_gov,
                'promul_date': promul_date,
                'enforce_date': enforce_date,
            })

            print(f"🏛️  [{ordin_type}] {ordin_name}")
            print(f"   ID: {ordin_id}")
            print(f"   지자체: {local_gov}")
            print(f"   공포일: {promul_date} | 시행일: {enforce_date}")
            print(f"   링크: https://www.law.go.kr/자치법규/{urllib.parse.quote(ordin_name)}")
            print()

    # 법령해석례 검색
    elif target == 'expc':
        for item in root.findall('.//expc'):
            expc_id = item.findtext('법령해석례일련번호', '')
            case_name = item.findtext('안건명', '')
            case_number = item.findtext('안건번호', '')
            request_org = item.findtext('질의기관명', '')
            response_org = item.findtext('회신기관명', '')
            response_date = item.findtext('회신일자', '')

            results.append({
                'id': expc_id,
                'name': case_name,
                'case_number': case_number,
                'request_org': request_org,
                'response_org': response_org,
                'response_date': response_date,
            })

            print(f"📝 {case_name}")
            print(f"   안건번호: {case_number}")
            print(f"   질의기관: {request_org} → 회신기관: {response_org}")
            print(f"   회신일: {response_date}")
            print()

    # 헌재결정례 검색
    elif target == 'detc':
        for item in root.findall('.//Detc'):
            detc_id = item.findtext('헌재결정례일련번호', '')
            case_name = item.findtext('사건명', '')
            case_number = item.findtext('사건번호', '')
            decision_date = item.findtext('종국일자', '')
            decision_type = item.findtext('결정유형', '')
            case_type = item.findtext('사건종류', '')

            results.append({
                'id': detc_id,
                'name': case_name,
                'case_number': case_number,
                'decision_date': decision_date,
                'decision_type': decision_type,
                'case_type': case_type,
            })

            print(f"⚖️  {case_name}")
            print(f"   사건번호: {case_number}")
            print(f"   종국일: {decision_date}")
            if decision_type:
                print(f"   결정유형: {decision_type}")
            print(f"   링크: https://www.law.go.kr/헌재결정례/({case_number.replace(' ', '')})")
            print()

    # 법령 검색 (기본)
    else:
        for item in root.findall('.//law'):
            law_id = item.findtext('법령ID', '')
            law_name = item.findtext('법령명한글', '') or item.findtext('법령명', '')
            promul_date = item.findtext('공포일자', '')
            enforce_date = item.findtext('시행일자', '')
            ministry = item.findtext('소관부처명', '')
            law_type = item.findtext('법령구분명', '')

            results.append({
                'id': law_id,
                'name': law_name,
                'promul_date': promul_date,
                'enforce_date': enforce_date,
                'ministry': ministry,
                'type': law_type,
            })

            print(f"📜 {law_name}")
            print(f"   ID: {law_id}")
            print(f"   구분: {law_type} | 소관: {ministry}")
            print(f"   공포일: {promul_date} | 시행일: {enforce_date}")
            print(f"   링크: https://www.law.go.kr/법령/{urllib.parse.quote(law_name)}")
            print()

    return results


def search_cases(query: str, court: str = None, from_date: str = None, display: int = 20, page: int = 1):
    """
    판례 전용 검색

    Args:
        query: 검색어
        court: 법원 필터 (대법원, 고등, 지방 등)
        from_date: 검색 시작일 (YYYYMMDD)
        display: 결과 개수
        page: 페이지 번호
    """
    oc = load_config()

    params = {
        'OC': oc,
        'target': 'prec',
        'type': 'XML',
        'query': query,
        'display': display,
        'page': page,
    }

    # 날짜 필터 (선고일 기준)
    if from_date:
        params['sort'] = 'date'

    root = api_request('lawSearch.do', params)

    total = root.findtext('.//totalCnt', '0')
    print(f"\n=== 판례 검색 결과: '{query}' (총 {total}건) ===\n")

    results = []
    for item in root.findall('.//prec'):
        case_id = item.findtext('판례일련번호', '')
        case_name = item.findtext('사건명', '')
        case_number = item.findtext('사건번호', '')
        court_name = item.findtext('법원명', '')
        judge_date = item.findtext('선고일자', '')
        case_type = item.findtext('사건종류명', '')
        judgment_type = item.findtext('판결유형', '')

        # 법원 필터링
        if court and court not in court_name:
            continue

        # 날짜 필터링
        if from_date and judge_date and judge_date < from_date:
            continue

        results.append({
            'id': case_id,
            'name': case_name,
            'case_number': case_number,
            'court': court_name,
            'judge_date': judge_date,
            'type': case_type,
            'judgment_type': judgment_type,
        })

        # 판례 인용 형식으로 출력
        formatted_date = format_court_date(judge_date) if judge_date else ''
        print(f"⚖️  {court_name} {formatted_date} 선고 {case_number} 판결")
        print(f"   사건명: {case_name}")
        print(f"   사건종류: {case_type}")
        print(f"   링크: https://www.law.go.kr/판례/({case_number.replace(' ', '')})")
        print()

    print(f"총 {len(results)}건")
    return results


def format_court_date(date_str: str) -> str:
    """선고일자 포맷팅 (20230112 → 2023. 1. 12.)"""
    if len(date_str) == 8:
        year = date_str[:4]
        month = str(int(date_str[4:6]))
        day = str(int(date_str[6:8]))
        return f"{year}. {month}. {day}."
    return date_str


def find_cached_law(law_id: str = None, law_name: str = None) -> Path | None:
    """
    캐시된 법령 파일 찾기

    Args:
        law_id: 법령 ID
        law_name: 법령명

    Returns:
        캐시된 파일 경로 또는 None
    """
    if not DATA_RAW_DIR.exists():
        return None

    for filepath in DATA_RAW_DIR.glob("*.xml"):
        if law_id and law_id in filepath.name:
            return filepath
        if law_name:
            safe_name = "".join(c for c in law_name if c.isalnum() or c in (' ', '_', '-')).strip()
            if safe_name in filepath.name:
                return filepath
    return None


def fetch_law_by_id(law_id: str, save: bool = True, force: bool = False):
    """
    법령 ID로 본문 조회

    Args:
        law_id: 법령 일련번호
        save: 파일로 저장 여부
        force: 캐시 무시하고 강제 다운로드
    """
    # 캐시 확인
    if not force:
        cached = find_cached_law(law_id=law_id)
        if cached:
            print(f"\n✅ 캐시된 파일 사용: {cached}")
            tree = ET.parse(cached)
            root = tree.getroot()
            law_name = root.findtext('.//법령명_한글', '') or root.findtext('.//법령명', '')
            promul_date = root.findtext('.//공포일자', '')
            enforce_date = root.findtext('.//시행일자', '')
            print(f"=== {law_name} ===")
            print(f"공포일: {promul_date} | 시행일: {enforce_date}")
            print(f"(강제 다운로드: --force 옵션 사용)")
            return root

    oc = load_config()

    params = {
        'OC': oc,
        'target': 'law',
        'type': 'XML',
        'ID': law_id,
    }

    root = api_request('lawService.do', params)

    # 기본 정보 추출
    law_name = root.findtext('.//법령명_한글', '') or root.findtext('.//법령명', '')
    promul_date = root.findtext('.//공포일자', '')
    enforce_date = root.findtext('.//시행일자', '')

    print(f"\n=== {law_name} ===")
    print(f"공포일: {promul_date} | 시행일: {enforce_date}")

    if save:
        # 파일명에서 특수문자 제거
        safe_name = "".join(c for c in law_name if c.isalnum() or c in (' ', '_', '-')).strip()
        filename = f"{safe_name}_{law_id}.xml"
        filepath = DATA_RAW_DIR / filename

        # XML 저장
        DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
        tree = ET.ElementTree(root)
        tree.write(filepath, encoding='utf-8', xml_declaration=True)
        print(f"\n저장됨: {filepath}")

    return root


def fetch_law_by_name(name: str, with_decree: bool = False, force: bool = False):
    """법령명으로 검색 후 첫 번째 결과 다운로드"""
    # 캐시 확인
    if not force:
        cached = find_cached_law(law_name=name)
        if cached:
            print(f"\n✅ 캐시된 파일 사용: {cached}")
            tree = ET.parse(cached)
            root = tree.getroot()
            law_name = root.findtext('.//법령명_한글', '') or root.findtext('.//법령명', '')
            promul_date = root.findtext('.//공포일자', '')
            enforce_date = root.findtext('.//시행일자', '')
            print(f"=== {law_name} ===")
            print(f"공포일: {promul_date} | 시행일: {enforce_date}")
            print(f"(강제 다운로드: --force 옵션 사용)")
            return root

    results = search_laws(name, display=5)

    if not results:
        print(f"Error: '{name}' 검색 결과가 없습니다.", file=sys.stderr)
        sys.exit(1)

    # 정확히 일치하는 법령 찾기
    exact_match = None
    for r in results:
        if r['name'] == name or r['name'].replace(' ', '') == name.replace(' ', ''):
            exact_match = r
            break

    target = exact_match or results[0]
    law_id = target['id']
    print(f"\n'{target['name']}' 다운로드 중...")
    root = fetch_law_by_id(law_id, force=True)  # 이미 캐시 확인했으므로 force=True

    # 시행령도 함께 다운로드
    if with_decree:
        decree_name = f"{name}시행령"
        print(f"\n'{decree_name}' 검색 중...")
        decree_results = search_laws(decree_name, display=3)

        if decree_results:
            for dr in decree_results:
                if '시행령' in dr['name']:
                    print(f"'{dr['name']}' 다운로드 중...")
                    fetch_law_by_id(dr['id'])
                    break

        # 시행규칙도 검색
        rule_name = f"{name}시행규칙"
        print(f"\n'{rule_name}' 검색 중...")
        rule_results = search_laws(rule_name, display=3)

        if rule_results:
            for rr in rule_results:
                if '시행규칙' in rr['name']:
                    print(f"'{rr['name']}' 다운로드 중...")
                    fetch_law_by_id(rr['id'])
                    break

    return root


def get_recent_laws(days: int = 30, from_date: str = None, to_date: str = None, target: str = "law"):
    """
    최근 개정 법령 조회

    Args:
        days: 최근 N일
        from_date: 시작일 (YYYYMMDD)
        to_date: 종료일 (YYYYMMDD)
        target: 검색 대상
    """
    oc = load_config()

    # 날짜 범위 계산
    if from_date and to_date:
        date_range = f"{from_date}~{to_date}"
    else:
        end = datetime.now()
        start = end - timedelta(days=days)
        date_range = f"{start.strftime('%Y%m%d')}~{end.strftime('%Y%m%d')}"

    params = {
        'OC': oc,
        'target': target,
        'type': 'XML',
        'display': 100,
        'sort': 'date',  # 날짜순 정렬
    }

    # 공포일자 범위로 검색 (efYd: 시행일자)
    # API에서 날짜 범위 파라미터명 확인 필요

    root = api_request('lawSearch.do', params)

    print(f"\n=== 최근 법령 목록 ({date_range}) ===\n")

    results = []
    for item in root.findall('.//law'):
        law_id = item.findtext('법령ID', '')
        law_name = item.findtext('법령명한글', '') or item.findtext('법령명', '')
        promul_date = item.findtext('공포일자', '')
        enforce_date = item.findtext('시행일자', '')
        ministry = item.findtext('소관부처명', '')
        revision_type = item.findtext('제개정구분명', '')

        # 날짜 필터링
        if from_date and to_date:
            if promul_date and (promul_date < from_date or promul_date > to_date):
                continue

        results.append({
            'id': law_id,
            'name': law_name,
            'promul_date': promul_date,
            'enforce_date': enforce_date,
            'ministry': ministry,
            'revision_type': revision_type,
        })

        revision_emoji = "🆕" if revision_type == "제정" else "📝"
        print(f"{revision_emoji} [{revision_type}] {law_name}")
        print(f"   공포일: {promul_date} | 시행일: {enforce_date}")
        print(f"   소관: {ministry}")
        print()

    print(f"총 {len(results)}건")
    return results


def fetch_case_by_id(case_id: str, save: bool = True):
    """
    판례 ID로 본문 조회

    Args:
        case_id: 판례일련번호
        save: 파일로 저장 여부
    """
    oc = load_config()

    params = {
        'OC': oc,
        'target': 'prec',
        'type': 'XML',
        'ID': case_id,
    }

    root = api_request('lawService.do', params)

    # 기본 정보 추출
    case_name = root.findtext('.//사건명', '')
    case_number = root.findtext('.//사건번호', '')
    court_name = root.findtext('.//법원명', '')
    judge_date = root.findtext('.//선고일자', '')

    print(f"\n=== {case_name} ===")
    print(f"사건번호: {case_number}")
    print(f"법원: {court_name} | 선고일: {format_court_date(judge_date)}")

    # 판시사항
    points = root.findtext('.//판시사항', '')
    if points:
        print(f"\n【판시사항】")
        points_clean = re.sub(r'<br\s*/?>', '\n', points)
        points_clean = re.sub(r'<[^>]+>', '', points_clean)
        print(points_clean.strip())

    # 판결요지
    summary = root.findtext('.//판결요지', '')
    if summary:
        print(f"\n【판결요지】")
        summary_clean = re.sub(r'<br\s*/?>', '\n', summary)
        summary_clean = re.sub(r'<[^>]+>', '', summary_clean)
        print(summary_clean.strip())

    if save:
        # 파일명에서 특수문자 제거
        safe_name = "".join(c for c in case_number if c.isalnum() or c in (' ', '_', '-')).strip()
        filename = f"{safe_name}_{case_id}.xml"
        filepath = DATA_RAW_DIR / "prec" / filename

        # XML 저장
        filepath.parent.mkdir(parents=True, exist_ok=True)
        tree = ET.ElementTree(root)
        tree.write(filepath, encoding='utf-8', xml_declaration=True)
        print(f"\n저장됨: {filepath}")

    return root


def fetch_case_by_number(case_number: str):
    """사건번호로 검색 후 첫 번째 결과 다운로드"""
    results = search_cases(case_number, display=5)

    if not results:
        print(f"Error: '{case_number}' 검색 결과가 없습니다.", file=sys.stderr)
        sys.exit(1)

    # 정확히 일치하는 판례 찾기
    exact_match = None
    clean_number = case_number.replace(' ', '')
    for r in results:
        if r['case_number'].replace(' ', '') == clean_number:
            exact_match = r
            break

    target = exact_match or results[0]
    case_id = target['id']
    print(f"\n'{target['case_number']}' 다운로드 중...")
    return fetch_case_by_id(case_id)


def main():
    parser = argparse.ArgumentParser(description='Korean Law Fetcher')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # search 명령
    search_parser = subparsers.add_parser('search', help='법령/판례 검색')
    search_parser.add_argument('query', help='검색어')
    search_parser.add_argument('--type', default='law',
                               choices=['law', 'prec', 'ordin', 'admrul', 'expc', 'detc'],
                               help='검색 대상 (law: 법령, prec: 판례, ordin: 자치법규, admrul: 행정규칙, expc: 법령해석례, detc: 헌재결정례)')
    search_parser.add_argument('--display', type=int, default=20, help='결과 개수')
    search_parser.add_argument('--page', type=int, default=1, help='페이지 번호')
    search_parser.add_argument('--sort', choices=['date', 'name'], help='정렬 기준 (date: 날짜순, name: 이름순)')

    # cases 명령 (판례 전용)
    cases_parser = subparsers.add_parser('cases', help='판례 검색')
    cases_parser.add_argument('query', help='검색어')
    cases_parser.add_argument('--court', help='법원 필터 (대법원, 고등, 지방)')
    cases_parser.add_argument('--from', dest='from_date', help='검색 시작일 (YYYYMMDD)')
    cases_parser.add_argument('--display', type=int, default=20, help='결과 개수')
    cases_parser.add_argument('--page', type=int, default=1, help='페이지 번호')

    # fetch 명령
    fetch_parser = subparsers.add_parser('fetch', help='법령/판례 다운로드')
    fetch_parser.add_argument('--id', help='법령/판례 ID')
    fetch_parser.add_argument('--name', help='법령명')
    fetch_parser.add_argument('--case', help='판례 사건번호 (예: 2022다12345)')
    fetch_parser.add_argument('--with-decree', action='store_true',
                              help='시행령/시행규칙도 함께 다운로드')
    fetch_parser.add_argument('--force', action='store_true',
                              help='캐시 무시하고 강제 다운로드')

    # recent 명령
    recent_parser = subparsers.add_parser('recent', help='최근 개정 법령')
    recent_parser.add_argument('--days', type=int, default=30, help='최근 N일')
    recent_parser.add_argument('--from', dest='from_date', help='시작일 (YYYYMMDD)')
    recent_parser.add_argument('--to', dest='to_date', help='종료일 (YYYYMMDD)')

    args = parser.parse_args()

    if args.command == 'search':
        search_laws(args.query, args.type, args.display, args.page, args.sort)
    elif args.command == 'cases':
        search_cases(args.query, args.court, args.from_date, args.display, args.page)
    elif args.command == 'fetch':
        if args.case:
            fetch_case_by_number(args.case)
        elif args.id:
            fetch_law_by_id(args.id, force=args.force)
        elif args.name:
            fetch_law_by_name(args.name, args.with_decree, args.force)
        else:
            print("Error: --id, --name, 또는 --case 중 하나를 지정하세요.", file=sys.stderr)
            sys.exit(1)
    elif args.command == 'recent':
        get_recent_laws(args.days, args.from_date, args.to_date)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
