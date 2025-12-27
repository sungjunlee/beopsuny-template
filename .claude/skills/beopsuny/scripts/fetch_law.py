#!/usr/bin/env python3
"""
Korean Law Fetcher - 국가법령정보센터 API 클라이언트

Usage:
    python fetch_law.py search "검색어" [--type law|prec|ordin|admrul|expc|detc]
    python fetch_law.py cases "검색어" [--court 대법원|고등|지방] [--from YYYYMMDD]
    python fetch_law.py fetch --id 법령ID [--with-decree]
    python fetch_law.py fetch --name "법령명" [--with-decree]
    python fetch_law.py recent [--days 30] [--from YYYYMMDD] [--to YYYYMMDD]
    python fetch_law.py checklist list
    python fetch_law.py checklist show <name> [--output FILE]
"""

import argparse
import calendar
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

import yaml

# 게이트웨이 유틸리티 (해외 접근 지원)
try:
    from gateway import fetch_url, is_gateway_configured
    HAS_GATEWAY = True
except ImportError:
    HAS_GATEWAY = False

# 중앙화된 경로 상수 사용 (common/paths.py)
from common.paths import (
    CONFIG_PATH,
    LAW_INDEX_PATH,
    CHECKLISTS_DIR,
    CALENDAR_PATH,
    DATA_RAW_DIR,
    DATA_PARSED_DIR,
    API_BASE_URL,
)

# API 기본 URL (common/paths.py에서 가져옴)
BASE_URL = API_BASE_URL

# 환경변수 이름
ENV_OC_CODE = "BEOPSUNY_OC_CODE"

# 검색 대상 타입 표시명
TARGET_TYPE_NAMES = {
    'law': '법령',
    'prec': '판례',
    'ordin': '자치법규',
    'admrul': '행정규칙',
    'expc': '법령해석례',
    'detc': '헌재결정례',
}

# 자치법규 종류 코드 매핑
ORDIN_TYPE_MAP = {
    'C0001': '조례',
    'C0002': '규칙',
}

# 캐시
_config_cache = None
_law_index_cache = None


def _sanitize_filename(name: str) -> str:
    """파일명에서 특수문자 제거

    Returns:
        안전한 파일명 (빈 문자열인 경우 'unnamed' 반환)
    """
    cleaned = "".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).strip()
    return cleaned or 'unnamed'


def _clean_html_text(text: str, preserve_breaks: bool = False, max_length: int = None) -> str:
    """HTML 태그 제거 및 텍스트 정리

    Args:
        text: HTML이 포함된 텍스트
        preserve_breaks: <br> 태그를 줄바꿈으로 변환할지 여부
        max_length: 최대 길이 (초과시 ... 추가)
    """
    if preserve_breaks:
        text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = text.strip()

    if max_length and len(text) > max_length:
        return text[:max_length] + "..."
    return text


def _load_config_file():
    """설정 파일 로드 (캐싱)"""
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            _config_cache = yaml.safe_load(f) or {}
    else:
        _config_cache = {}

    return _config_cache


def _load_law_index():
    """법령 인덱스 파일 로드 (캐싱)"""
    global _law_index_cache
    if _law_index_cache is not None:
        return _law_index_cache

    if LAW_INDEX_PATH.exists():
        with open(LAW_INDEX_PATH, 'r', encoding='utf-8') as f:
            _law_index_cache = yaml.safe_load(f) or {}
    else:
        _law_index_cache = {}

    return _law_index_cache


def load_config():
    """OC 코드 로드 (환경변수 > 설정파일)"""
    # 1. 환경변수 우선
    oc_code = os.environ.get(ENV_OC_CODE)
    if oc_code:
        return oc_code

    # 2. 설정 파일 fallback
    config = _load_config_file()
    oc_code = config.get('oc_code', '')

    if not oc_code:
        print(f"Error: OC code not found.", file=sys.stderr)
        print(f"", file=sys.stderr)
        print(f"Set one of the following:", file=sys.stderr)
        print(f"  1. Environment variable: export {ENV_OC_CODE}=your_oc_code", file=sys.stderr)
        print(f"  2. Config file: {CONFIG_PATH}", file=sys.stderr)
        print(f"", file=sys.stderr)
        print(f"Get your OC code at: https://open.law.go.kr", file=sys.stderr)
        sys.exit(1)

    return oc_code


def get_major_law_id(name: str) -> str | None:
    """주요 법령의 ID를 law_index.yaml에서 조회"""
    law_index = _load_law_index()
    major_laws = law_index.get('major_laws', {})

    # 정확한 이름으로 먼저 검색
    if name in major_laws:
        return major_laws[name]

    # 공백 제거 후 검색
    clean_name = name.replace(' ', '')
    for law_name, law_id in major_laws.items():
        if law_name.replace(' ', '') == clean_name:
            return law_id

    return None


def api_request(endpoint: str, params: dict) -> ET.Element:
    """API 요청 및 XML 파싱 (게이트웨이 자동 사용)"""
    url = f"{BASE_URL}/{endpoint}?{urllib.parse.urlencode(params)}"

    try:
        # 게이트웨이 유틸리티 사용 (설정되어 있으면 자동 사용)
        if HAS_GATEWAY:
            try:
                content = fetch_url(url, timeout=30)
            except ValueError as e:
                # 게이트웨이 미설정 시 직접 시도
                print(f"Note: {e}", file=sys.stderr)
                print("Attempting direct connection...", file=sys.stderr)
                content = None

            if content is not None:
                # HTML 응답 감지
                if content.strip().startswith('<!DOCTYPE') or content.strip().startswith('<html'):
                    print(f"Error: API returned HTML instead of XML.", file=sys.stderr)
                    print(f"This usually means overseas access is blocked.", file=sys.stderr)
                    print(f"", file=sys.stderr)
                    print(f"Solution: Configure cors-anywhere gateway:", file=sys.stderr)
                    print(f"  export BEOPSUNY_GATEWAY_URL='https://your-gateway.example.com'", file=sys.stderr)
                    sys.exit(1)

                return ET.fromstring(content)

        # 직접 접근 (게이트웨이 미설정)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read().decode('utf-8')

            # HTML 응답 감지 (API 오류 시 HTML 반환됨)
            if content.strip().startswith('<!DOCTYPE') or content.strip().startswith('<html'):
                print(f"Error: API returned HTML instead of XML.", file=sys.stderr)
                print(f"This usually means overseas access is blocked.", file=sys.stderr)
                print(f"", file=sys.stderr)
                print(f"Solution: Configure cors-anywhere gateway:", file=sys.stderr)
                print(f"  export BEOPSUNY_GATEWAY_URL='https://your-gateway.example.com'", file=sys.stderr)
                print(f"", file=sys.stderr)
                print(f"URL: {url}", file=sys.stderr)
                sys.exit(1)

            return ET.fromstring(content)
    except urllib.error.HTTPError as e:
        print(f"Error: HTTP {e.code} - {e.reason}", file=sys.stderr)
        if e.code == 403:
            print(f"", file=sys.stderr)
            print(f"403 Forbidden - overseas access may be blocked.", file=sys.stderr)
            print(f"Configure gateway: export BEOPSUNY_GATEWAY_URL='https://...'", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: API request failed - {e}", file=sys.stderr)
        sys.exit(1)
    except ET.ParseError as e:
        print(f"Error: Failed to parse XML response - {e}", file=sys.stderr)
        print(f"", file=sys.stderr)
        print(f"This may indicate the API returned an error page instead of XML.", file=sys.stderr)
        print(f"URL: {url}", file=sys.stderr)
        sys.exit(1)


def search_laws(query: str, target: str = "law", display: int = 20, page: int = 1, sort: str = None, output_format: str = "text"):
    """
    법령 검색

    Args:
        query: 검색어
        target: 검색 대상 (law: 법령, prec: 판례, ordin: 자치법규, admrul: 행정규칙, expc: 법령해석례, detc: 헌재결정례)
        display: 결과 개수 (최대 100)
        page: 페이지 번호
        sort: 정렬 기준 (date: 날짜순, name: 이름순)
        output_format: 출력 형식 (text: 텍스트, json: JSON)
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

    target_name = TARGET_TYPE_NAMES.get(target, target)

    # JSON 출력 모드에서는 텍스트 출력 생략
    is_json = output_format == 'json'
    if not is_json:
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

            if not is_json:
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

            if not is_json:
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

            if not is_json:
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

            if not is_json:
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

            if not is_json:
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

            if not is_json:
                print(f"📜 {law_name}")
                print(f"   ID: {law_id}")
                print(f"   구분: {law_type} | 소관: {ministry}")
                print(f"   공포일: {promul_date} | 시행일: {enforce_date}")
                print(f"   링크: https://www.law.go.kr/법령/{urllib.parse.quote(law_name)}")
                print()

    # JSON 출력
    if is_json:
        output = {
            'query': query,
            'target': target,
            'total': int(total),
            'page': page,
            'display': display,
            'results': results,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))

    return results


def search_cases(query: str, court: str = None, from_date: str = None, display: int = 20, page: int = 1, output_format: str = "text"):
    """
    판례 전용 검색

    Args:
        query: 검색어
        court: 법원 필터 (대법원, 고등, 지방 등)
        from_date: 검색 시작일 (YYYYMMDD)
        display: 결과 개수
        page: 페이지 번호
        output_format: 출력 형식 (text: 텍스트, json: JSON)
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
    is_json = output_format == 'json'
    if not is_json:
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

        if not is_json:
            # 판례 인용 형식으로 출력
            formatted_date = format_court_date(judge_date) if judge_date else ''
            print(f"⚖️  {court_name} {formatted_date} 선고 {case_number} 판결")
            print(f"   사건명: {case_name}")
            print(f"   사건종류: {case_type}")
            print(f"   링크: https://www.law.go.kr/판례/({case_number.replace(' ', '')})")
            print()

    if is_json:
        output = {
            'query': query,
            'total': int(total),
            'page': page,
            'display': display,
            'court_filter': court,
            'from_date': from_date,
            'results': results,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
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
            safe_name = _sanitize_filename(law_name)
            if safe_name in filepath.name:
                return filepath
    return None


def fetch_law_by_id(law_id: str, save: bool = True, force: bool = False, target: str = "law"):
    """
    법령/행정규칙 등 ID로 본문 조회

    Args:
        law_id: 법령/행정규칙 일련번호
        save: 파일로 저장 여부
        force: 캐시 무시하고 강제 다운로드
        target: 검색 대상 (law, admrul, prec, ordin, expc, detc)
    """
    # 캐시 확인 (법령만)
    if not force and target == "law":
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

    # 자치법규는 MST 파라미터 사용 (다른 타입은 ID)
    params = {
        'OC': oc,
        'target': target,
        'type': 'XML',
    }
    if target == 'ordin':
        params['MST'] = law_id
    else:
        params['ID'] = law_id

    root = api_request('lawService.do', params)

    # API 오류 응답 감지 (일치하는 데이터 없음)
    error_text = root.text.strip() if root.text else ''
    if '일치하는' in error_text and '없습니다' in error_text:
        target_name = TARGET_TYPE_NAMES.get(target, target)
        print(f"\n❌ 오류: ID '{law_id}'에 해당하는 {target_name}을(를) 찾을 수 없습니다.", file=sys.stderr)
        print(f"   API 응답: {error_text}", file=sys.stderr)
        sys.exit(1)

    # target 타입에 따라 다른 필드 추출 및 저장
    if target == 'admrul':
        # 행정규칙
        item_name = root.findtext('.//행정규칙명', '') or root.findtext('.//행정규칙명한글', '')
        promul_date = root.findtext('.//발령일자', '')
        enforce_date = root.findtext('.//시행일자', '')
        ministry = root.findtext('.//소관부처', '') or root.findtext('.//소관부처명', '')
        admrul_type = root.findtext('.//행정규칙종류', '')

        print(f"\n=== [{admrul_type}] {item_name} ===")
        print(f"소관: {ministry}")
        print(f"발령일: {promul_date} | 시행일: {enforce_date}")

        if save:
            safe_name = _sanitize_filename(item_name)
            filename = f"{safe_name}_{law_id}.xml"
            filepath = DATA_RAW_DIR / "admrul" / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            tree = ET.ElementTree(root)
            tree.write(filepath, encoding='utf-8', xml_declaration=True)
            print(f"\n저장됨: {filepath}")

    elif target == 'ordin':
        # 자치법규
        item_name = root.findtext('.//자치법규명', '')
        promul_date = root.findtext('.//공포일자', '')
        enforce_date = root.findtext('.//시행일자', '')
        local_gov = root.findtext('.//지자체기관명', '')
        ordin_type = root.findtext('.//자치법규종류', '')

        # 자치법규종류 코드를 한글로 변환
        ordin_type_name = ORDIN_TYPE_MAP.get(ordin_type, ordin_type)

        print(f"\n=== [{ordin_type_name}] {item_name} ===")
        print(f"지자체: {local_gov}")
        print(f"공포일: {promul_date} | 시행일: {enforce_date}")

        if save:
            safe_name = _sanitize_filename(item_name)
            filename = f"{safe_name}_{law_id}.xml"
            filepath = DATA_RAW_DIR / "ordin" / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            tree = ET.ElementTree(root)
            tree.write(filepath, encoding='utf-8', xml_declaration=True)
            print(f"\n저장됨: {filepath}")

    elif target == 'expc':
        # 법령해석례
        item_name = root.findtext('.//안건명', '')
        case_number = root.findtext('.//안건번호', '')
        response_date = root.findtext('.//해석일자', '')
        request_org = root.findtext('.//질의기관명', '')
        response_org = root.findtext('.//해석기관명', '')

        print(f"\n=== 법령해석례: {item_name} ===")
        print(f"안건번호: {case_number}")
        print(f"질의: {request_org} → 해석: {response_org}")
        print(f"해석일: {response_date}")

        # 질의요지/회답 출력
        question = root.findtext('.//질의요지', '')
        answer = root.findtext('.//회답', '')
        if question:
            print(f"\n【질의요지】")
            print(question[:500] + "..." if len(question) > 500 else question)
        if answer:
            print(f"\n【회답】")
            print(answer[:500] + "..." if len(answer) > 500 else answer)

        if save:
            safe_name = _sanitize_filename(case_number)
            filename = f"{safe_name}_{law_id}.xml"
            filepath = DATA_RAW_DIR / "expc" / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            tree = ET.ElementTree(root)
            tree.write(filepath, encoding='utf-8', xml_declaration=True)
            print(f"\n저장됨: {filepath}")

    elif target == 'detc':
        # 헌재결정례
        item_name = root.findtext('.//사건명', '')
        case_number = root.findtext('.//사건번호', '')
        decision_date = root.findtext('.//종국일자', '')
        case_type = root.findtext('.//사건종류명', '')

        print(f"\n=== 헌재결정례: {item_name} ===")
        print(f"사건번호: {case_number}")
        print(f"사건종류: {case_type}")
        print(f"종국일: {decision_date}")

        # 판시사항/결정요지 출력
        points = root.findtext('.//판시사항', '')
        summary = root.findtext('.//결정요지', '')
        if points:
            print(f"\n【판시사항】")
            print(_clean_html_text(points, max_length=500))
        if summary:
            print(f"\n【결정요지】")
            print(_clean_html_text(summary, max_length=500))

        if save:
            safe_name = _sanitize_filename(case_number)
            filename = f"{safe_name}_{law_id}.xml"
            filepath = DATA_RAW_DIR / "detc" / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            tree = ET.ElementTree(root)
            tree.write(filepath, encoding='utf-8', xml_declaration=True)
            print(f"\n저장됨: {filepath}")

    elif target == 'prec':
        # 판례 (fetch_case_by_id와 동일한 로직)
        item_name = root.findtext('.//사건명', '')
        case_number = root.findtext('.//사건번호', '')
        court_name = root.findtext('.//법원명', '')
        judge_date = root.findtext('.//선고일자', '')

        print(f"\n=== {item_name} ===")
        print(f"사건번호: {case_number}")
        print(f"법원: {court_name} | 선고일: {format_court_date(judge_date)}")

        # 판시사항/판결요지 출력
        points = root.findtext('.//판시사항', '')
        summary = root.findtext('.//판결요지', '')
        if points:
            print(f"\n【판시사항】")
            print(_clean_html_text(points, preserve_breaks=True, max_length=500))
        if summary:
            print(f"\n【판결요지】")
            print(_clean_html_text(summary, preserve_breaks=True, max_length=500))

        if save:
            safe_name = _sanitize_filename(case_number)
            filename = f"{safe_name}_{law_id}.xml"
            filepath = DATA_RAW_DIR / "prec" / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            tree = ET.ElementTree(root)
            tree.write(filepath, encoding='utf-8', xml_declaration=True)
            print(f"\n저장됨: {filepath}")

    else:
        # 법령 (기본)
        item_name = root.findtext('.//법령명_한글', '') or root.findtext('.//법령명', '')
        promul_date = root.findtext('.//공포일자', '')
        enforce_date = root.findtext('.//시행일자', '')

        print(f"\n=== {item_name} ===")
        print(f"공포일: {promul_date} | 시행일: {enforce_date}")

        if save:
            safe_name = _sanitize_filename(item_name)
            filename = f"{safe_name}_{law_id}.xml"
            filepath = DATA_RAW_DIR / filename
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

    # 주요 법령인 경우 설정 파일에서 ID 직접 조회
    major_law_id = get_major_law_id(name)
    if major_law_id:
        print(f"📌 '{name}'은 주요 법령입니다. (ID: {major_law_id})")
        return fetch_law_by_id(major_law_id, force=True)

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


def get_recent_laws(days: int = 30, from_date: str = None, to_date: str = None, target: str = "law", date_type: str = "ef", output_format: str = "text"):
    """
    최근 개정 법령 조회

    Args:
        days: 최근 N일
        from_date: 시작일 (YYYYMMDD)
        to_date: 종료일 (YYYYMMDD)
        target: 검색 대상
        date_type: 날짜 기준 (ef: 시행일, anc: 공포일)
        output_format: 출력 형식 (text: 텍스트, json: JSON)
    """
    is_json = output_format == 'json'
    oc = load_config()

    # 날짜 범위 계산
    if from_date and to_date:
        date_range = f"{from_date}~{to_date}"
    else:
        end = datetime.now()
        start = end - timedelta(days=days)
        from_date = start.strftime('%Y%m%d')
        to_date = end.strftime('%Y%m%d')
        date_range = f"{from_date}~{to_date}"

    params = {
        'OC': oc,
        'target': target,
        'type': 'XML',
        'display': 100,
        'sort': 'efdes',  # 시행일자 내림차순
    }

    # 날짜 범위 파라미터 추가 (efYd: 시행일자, ancYd: 공포일자)
    if date_type == "anc":
        params['ancYd'] = date_range
        params['sort'] = 'ddes'  # 공포일자 내림차순
    else:
        params['efYd'] = date_range

    root = api_request('lawSearch.do', params)

    total = root.findtext('.//totalCnt', '0')
    date_type_name = "공포일" if date_type == "anc" else "시행일"
    if not is_json:
        print(f"\n=== 최근 법령 목록 ({date_type_name} 기준: {date_range}) - 총 {total}건 ===\n")

    results = []
    for item in root.findall('.//law'):
        law_id = item.findtext('법령ID', '')
        law_name = item.findtext('법령명한글', '') or item.findtext('법령명', '')
        promul_date = item.findtext('공포일자', '')
        enforce_date = item.findtext('시행일자', '')
        ministry = item.findtext('소관부처명', '')
        revision_type = item.findtext('제개정구분명', '')

        results.append({
            'id': law_id,
            'name': law_name,
            'promul_date': promul_date,
            'enforce_date': enforce_date,
            'ministry': ministry,
            'revision_type': revision_type,
        })

        if not is_json:
            revision_emoji = "🆕" if revision_type == "제정" else "📝"
            print(f"{revision_emoji} [{revision_type}] {law_name}")
            print(f"   공포일: {promul_date} | 시행일: {enforce_date}")
            print(f"   소관: {ministry}")
            print()

    if is_json:
        output = {
            'date_range': date_range,
            'date_type': date_type_name,
            'total': int(total),
            'results': results,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"표시: {len(results)}건 / 전체: {total}건")

    return results


def search_exact_law(name: str, with_admrul: bool = False, output_format: str = "text"):
    """
    정확한 법령명으로 검색 (클라이언트측 필터링)

    Args:
        name: 정확한 법령명 (예: "상법", "민법")
        with_admrul: 관련 행정규칙도 함께 검색 여부
        output_format: 출력 형식 (text: 텍스트, json: JSON)

    Note:
        API는 부분 일치 검색만 지원하므로, 결과에서 정확히 일치하는 것만 필터링
    """
    is_json = output_format == 'json'

    # 주요 법령인 경우 설정 파일에서 ID 직접 활용
    major_law_id = get_major_law_id(name)
    if major_law_id and not is_json:
        print(f"\n💡 '{name}'은 주요 법령입니다. 직접 조회합니다...")
        print(f"   → python scripts/fetch_law.py fetch --id {major_law_id}\n")

    oc = load_config()

    # 충분한 결과를 가져와서 필터링
    params = {
        'OC': oc,
        'target': 'law',
        'type': 'XML',
        'query': name,
        'display': 100,
    }

    root = api_request('lawSearch.do', params)

    if not is_json:
        print(f"\n=== 법령 정확 검색: '{name}' ===\n")

    results = []
    exact_matches = []
    related_matches = []

    for item in root.findall('.//law'):
        law_id = item.findtext('법령ID', '')
        law_name = item.findtext('법령명한글', '') or item.findtext('법령명', '')
        promul_date = item.findtext('공포일자', '')
        enforce_date = item.findtext('시행일자', '')
        ministry = item.findtext('소관부처명', '')
        law_type = item.findtext('법령구분명', '')

        result = {
            'id': law_id,
            'name': law_name,
            'promul_date': promul_date,
            'enforce_date': enforce_date,
            'ministry': ministry,
            'type': law_type,
        }

        # 정확히 일치하는지 확인
        clean_name = name.replace(' ', '')
        clean_law_name = law_name.replace(' ', '')

        if clean_law_name == clean_name:
            exact_matches.append(result)
        elif clean_law_name.startswith(clean_name) and ('시행령' in law_name or '시행규칙' in law_name):
            related_matches.append(result)

    # 정확히 일치하는 법령 출력
    if exact_matches:
        if not is_json:
            print("📌 정확히 일치하는 법령:\n")
            for r in exact_matches:
                print(f"📜 {r['name']}")
                print(f"   ID: {r['id']}")
                print(f"   구분: {r['type']} | 소관: {r['ministry']}")
                print(f"   공포일: {r['promul_date']} | 시행일: {r['enforce_date']}")
                print(f"   링크: https://www.law.go.kr/법령/{urllib.parse.quote(r['name'])}")
                print()
        results.extend(exact_matches)
    elif not is_json:
        print(f"⚠️  '{name}'과 정확히 일치하는 법령이 없습니다.\n")

    # 관련 법령 (시행령, 시행규칙) 출력
    if related_matches:
        if not is_json:
            print("📎 관련 법령 (시행령/시행규칙):\n")
            for r in related_matches:
                print(f"📜 {r['name']}")
                print(f"   ID: {r['id']}")
                print(f"   구분: {r['type']} | 소관: {r['ministry']}")
                print(f"   공포일: {r['promul_date']} | 시행일: {r['enforce_date']}")
                print()
        results.extend(related_matches)

    if not results and not is_json:
        print(f"💡 힌트: '{name}'을 포함하는 법령을 검색하려면:")
        print(f"   python scripts/fetch_law.py search \"{name}\"")

    # 관련 행정규칙 검색
    admin_rules = []
    if with_admrul:
        if not is_json:
            print(f"\n{'='*60}")
            print(f"📋 관련 행정규칙 (고시/훈령/예규) 검색 중...")
            print(f"{'='*60}")
        admin_rules = search_related_admin_rules(name, output_format=output_format)

    # JSON 출력
    if is_json:
        output = {
            'query': name,
            'exact_matches': exact_matches,
            'related_laws': related_matches,
            'admin_rules': admin_rules if with_admrul else [],
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))

    return results


def search_related_admin_rules(law_name: str, display: int = 10, output_format: str = "text"):
    """
    법령명과 관련된 행정규칙 검색

    Args:
        law_name: 법령명 (예: "개인정보보호법", "근로기준법")
        display: 표시할 결과 수
        output_format: 출력 형식 (text: 텍스트, json: JSON)
    """
    is_json = output_format == 'json'
    oc = load_config()

    # 다양한 검색 패턴 시도
    search_terms = [
        law_name,  # 법령명 그대로
        f"{law_name} 시행",  # 시행 관련
        f"{law_name} 기준",  # 기준 관련
    ]

    all_results = []
    seen_ids = set()

    for term in search_terms:
        params = {
            'OC': oc,
            'target': 'admrul',
            'type': 'XML',
            'query': term,
            'display': display,
        }

        try:
            root = api_request('lawSearch.do', params)

            for item in root.findall('.//admrul'):
                admrul_id = item.findtext('행정규칙일련번호', '')
                if admrul_id in seen_ids:
                    continue
                seen_ids.add(admrul_id)

                admrul_name = item.findtext('행정규칙명', '')
                admrul_type = item.findtext('행정규칙종류', '')
                promul_date = item.findtext('발령일자', '')
                enforce_date = item.findtext('시행일자', '')
                ministry = item.findtext('소관부처명', '')

                all_results.append({
                    'id': admrul_id,
                    'name': admrul_name,
                    'type': admrul_type,
                    'promul_date': promul_date,
                    'enforce_date': enforce_date,
                    'ministry': ministry,
                })
        except (urllib.error.HTTPError, urllib.error.URLError, ET.ParseError):
            # API 오류 시 다음 검색어로 계속
            continue

    if not is_json:
        if all_results:
            print(f"\n=== '{law_name}' 관련 행정규칙 (총 {len(all_results)}건) ===\n")
            print("⚠️  실무 팁: 법률은 큰 틀만 정합니다. 구체적인 기준/절차/서식은")
            print("   아래 행정규칙(고시/훈령/예규)에서 확인하세요!\n")

            for r in all_results[:display]:
                print(f"📋 [{r['type']}] {r['name']}")
                print(f"   ID: {r['id']}")
                print(f"   소관: {r['ministry']}")
                print(f"   발령일: {r['promul_date']} | 시행일: {r['enforce_date']}")
                print(f"   링크: https://www.law.go.kr/행정규칙/{urllib.parse.quote(r['name'])}")
                print()
        else:
            print(f"\n'{law_name}' 관련 행정규칙을 찾지 못했습니다.")
            print(f"💡 직접 검색: python scripts/fetch_law.py search \"{law_name}\" --type admrul")

    return all_results


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
        print(_clean_html_text(points, preserve_breaks=True))

    # 판결요지
    summary = root.findtext('.//판결요지', '')
    if summary:
        print(f"\n【판결요지】")
        print(_clean_html_text(summary, preserve_breaks=True))

    if save:
        safe_name = _sanitize_filename(case_number)
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


# ============================================================
# 체크리스트 기능
# ============================================================

def _generate_law_link(law_name: str, articles: list = None) -> str:
    """법령 링크 생성 (gen_link.py 로직 재사용)"""
    encoded_name = urllib.parse.quote(law_name)
    base_url = f"https://www.law.go.kr/법령/{encoded_name}"

    if articles:
        # 첫 번째 조항으로 앵커 링크 생성
        return base_url
    return base_url


def list_checklists():
    """사용 가능한 체크리스트/조사가이드 목록 출력"""
    if not CHECKLISTS_DIR.exists():
        print("체크리스트 디렉토리가 없습니다.", file=sys.stderr)
        return []

    checklists = []
    guides = []
    for filepath in sorted(CHECKLISTS_DIR.glob("*.yaml")):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if data:
                    item = {
                        'name': filepath.stem,
                        'title': data.get('name', filepath.stem),
                        'description': data.get('description', ''),
                        'category': data.get('category', ''),
                        'item_count': len(data.get('items', [])),
                        'type': data.get('type', 'checklist'),
                    }
                    if item['type'] == 'research_guide':
                        guides.append(item)
                    else:
                        checklists.append(item)
        except (yaml.YAMLError, OSError) as e:
            print(f"Warning: {filepath.name} 로드 실패 - {e}", file=sys.stderr)
            continue

    # 체크리스트 출력
    if checklists:
        print("\n=== 체크리스트 (절차적 점검) ===\n")
        for cl in checklists:
            print(f"📋 {cl['name']}")
            print(f"   제목: {cl['title']}")
            print(f"   설명: {cl['description']}")
            print(f"   분류: {cl['category']} | 항목 수: {cl['item_count']}개")
            print()

    # 조사 가이드 출력
    if guides:
        print("=== 조사 가이드 (탐색적 질문) ===\n")
        print("⚠️  조사 가이드는 '체크리스트'가 아닙니다!")
        print("   맥락에 따라 판단이 달라지므로, 질문을 시작점으로 심층 조사하세요.\n")
        for g in guides:
            print(f"🔍 {g['name']}")
            print(f"   제목: {g['title']}")
            print(f"   설명: {g['description']}")
            print(f"   분류: {g['category']} | 질문 수: {g['item_count']}개")
            print()

    print("사용법: python scripts/fetch_law.py checklist show <name>")
    print("예시: python scripts/fetch_law.py checklist show startup")
    return checklists + guides


def show_checklist(name: str, output_file: str = None, output_format: str = "markdown"):
    """체크리스트/조사가이드 출력 (법령 링크 자동 생성)

    Args:
        name: 체크리스트 이름 (확장자 없이)
        output_file: 출력 파일 경로 (없으면 stdout)
        output_format: 출력 형식 (markdown, json)
    """
    filepath = CHECKLISTS_DIR / f"{name}.yaml"

    if not filepath.exists():
        print(f"Error: '{name}' 체크리스트를 찾을 수 없습니다.", file=sys.stderr)
        print(f"사용 가능한 체크리스트: python scripts/fetch_law.py checklist list", file=sys.stderr)
        sys.exit(1)

    with open(filepath, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    # 빈 YAML 파일 체크
    if not data:
        print(f"Error: '{name}' 체크리스트가 비어있습니다.", file=sys.stderr)
        sys.exit(1)

    if output_format == 'json':
        # JSON 출력
        output = json.dumps(data, ensure_ascii=False, indent=2)
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"저장됨: {output_file}")
        else:
            print(output)
        return data

    # 타입 확인 (research_guide vs checklist)
    doc_type = data.get('type', 'checklist')
    is_research_guide = doc_type == 'research_guide'

    # Markdown 출력 생성
    lines = []
    lines.append(f"# {data.get('name', name)}")
    lines.append("")
    lines.append(f"> {data.get('description', '')}")
    lines.append("")

    # 경고 문구 (research_guide인 경우)
    warnings = data.get('warnings', [])
    if warnings:
        lines.append("### ⚠️ 중요")
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")

    lines.append(f"**분류**: {data.get('category', '')} | **최종 업데이트**: {data.get('last_updated', '')}")
    lines.append("")

    # 초기 분기 질문 (Quick Triage)
    triage = data.get('triage_questions', [])
    if triage:
        lines.append("## 🔀 초기 분기 질문")
        lines.append("")
        for t in triage:
            q = t.get('question', '')
            lines.append(f"**{q}**")
            if 'if_yes' in t:
                lines.append(f"  - Yes → {t['if_yes']}")
            if 'branches' in t:
                for b in t['branches']:
                    lines.append(f"  - {b}")
            if 'thresholds' in t:
                for th in t['thresholds']:
                    lines.append(f"  - {th}")
            if 'examples' in t:
                for ex in t['examples']:
                    lines.append(f"    - {ex}")
            lines.append("")
        lines.append("---")
        lines.append("")

    # 연관 체크리스트
    related = data.get('related_checklists', [])
    if related:
        lines.append("## 📎 연관 체크리스트")
        lines.append("")
        for r in related:
            lines.append(f"- **{r.get('name', '')}**: {r.get('when', '')}")
        lines.append("")
        lines.append("---")
        lines.append("")

    for i, item in enumerate(data.get('items', []), 1):
        if is_research_guide:
            # 조사 가이드 형식
            question = item.get('question', '')
            lines.append(f"## {i}. {question}")
            lines.append("")

            # 왜 중요한지
            why = item.get('why_it_matters', '')
            if why:
                lines.append("**왜 중요한가:**")
                for line in why.strip().split('\n'):
                    lines.append(f"> {line.strip()}")
                lines.append("")

            # 조사 액션
            research_actions = item.get('research_actions', [])
            if research_actions:
                lines.append("**조사 방법:**")
                for action in research_actions:
                    lines.append(f"```")
                    lines.append(action)
                    lines.append(f"```")
                lines.append("")

            # 핵심 질문
            key_questions = item.get('key_questions', [])
            if key_questions:
                lines.append("**검토할 질문:**")
                for q in key_questions:
                    lines.append(f"- ❓ {q}")
                lines.append("")

            # 위험 요소
            risk_factors = item.get('risk_factors', [])
            if risk_factors:
                lines.append("**위험 신호:**")
                for rf in risk_factors:
                    lines.append(f"- 🚨 {rf}")
                lines.append("")

            # 참고 사항
            note = item.get('note', '')
            if note:
                lines.append(f"**📌 참고**: {note}")
                lines.append("")

        else:
            # 기존 체크리스트 형식
            task = item.get('task', '')
            risk_level = item.get('risk_level', 'medium')
            risk_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(risk_level, '⚪')

            lines.append(f"## {i}. {task} {risk_emoji}")
            lines.append("")

            # 조건 표시
            condition = item.get('condition')
            if condition:
                lines.append(f"**조건**: {condition}")
                lines.append("")

            # 기한 표시
            deadline = item.get('deadline')
            if deadline:
                lines.append(f"**⚠️ 기한**: {deadline}")
                lines.append("")

            # 점검 사항
            check_points = item.get('check_points', [])
            if check_points:
                lines.append("**점검 사항**:")
                for cp in check_points:
                    lines.append(f"- [ ] {cp}")
                lines.append("")

            # 참고 사항
            notes = item.get('notes', '')
            if notes:
                lines.append("**참고**:")
                for note_line in notes.strip().split('\n'):
                    lines.append(f"> {note_line.strip()}")
                lines.append("")

        # 공통: 관련 법령 (링크 포함)
        laws = item.get('laws', item.get('related_laws', []))
        if laws:
            lines.append("**관련 법령**:")
            for law in laws:
                if not isinstance(law, dict):
                    continue
                law_name = law.get('name', '')
                if not law_name:
                    continue
                articles = law.get('articles', [])
                link = _generate_law_link(law_name)

                if articles:
                    articles_str = ", ".join(str(a) for a in articles if a)
                    lines.append(f"- [{law_name}]({link}): {articles_str}")
                else:
                    lines.append(f"- [{law_name}]({link})")
            lines.append("")

        # 공통: 관련 행정규칙
        admin_rules = item.get('admin_rules', [])
        if admin_rules:
            lines.append("**관련 행정규칙 (고시/훈령)**:")
            for rule in admin_rules:
                if not isinstance(rule, str):
                    continue
                rule_link = f"https://www.law.go.kr/행정규칙/{urllib.parse.quote(rule)}"
                lines.append(f"- [{rule}]({rule_link})")
            lines.append("")

        lines.append("---")
        lines.append("")

    # 조사 워크플로우 (research_guide인 경우)
    workflow = data.get('research_workflow', {})
    if workflow:
        lines.append("## 조사 워크플로우")
        lines.append("")
        for step_key in sorted(workflow.keys()):
            step = workflow[step_key]
            lines.append(f"**{step.get('name', step_key)}**: {step.get('action', '')}")
        lines.append("")
        lines.append("---")
        lines.append("")

    # 이 가이드에서 다루지 않는 주요 이슈 (research_guide)
    not_covered = data.get('not_covered', [])
    if not_covered and isinstance(not_covered, list):
        lines.append("## ⚠️ 이 가이드에서 다루지 않는 이슈")
        lines.append("")
        for nc in not_covered:
            if isinstance(nc, dict):
                area = nc.get('area', '')
                lines.append(f"**{area}** ({nc.get('when_relevant', '')})")
                for issue in nc.get('issues', []):
                    lines.append(f"  - {issue}")
            elif isinstance(nc, str):
                lines.append(f"- {nc}")
            lines.append("")
        lines.append("---")
        lines.append("")

    # 놓치기 쉬운 항목 (Common Oversights)
    oversights = data.get('common_oversights', [])
    if oversights:
        lines.append("## 💡 놓치기 쉬운 항목")
        lines.append("")
        for o in oversights:
            item_name = o.get('item', '')
            issue = o.get('issue', '')
            action = o.get('action', o.get('tip', ''))
            lines.append(f"**{item_name}**")
            lines.append(f"  - 문제: {issue}")
            lines.append(f"  - 조치: {action}")
            lines.append("")
        lines.append("---")
        lines.append("")

    # 성장 단계별 검토 (startup)
    growth = data.get('growth_stage_considerations', {})
    if growth:
        lines.append("## 📈 성장 단계별 추가 검토")
        lines.append("")
        for stage, items in growth.items():
            stage_name = {'seed_stage': '🌱 Seed', 'series_a_plus': '🚀 Series A+', 'scaling': '📊 Scaling'}.get(stage, stage)
            lines.append(f"**{stage_name}**")
            for item in items:
                lines.append(f"  - {item}")
            lines.append("")
        lines.append("---")
        lines.append("")

    # 주기적 점검 (privacy)
    periodic = data.get('periodic_review', {})
    if periodic:
        lines.append("## 🔄 주기적 점검 사항")
        lines.append("")
        if 'annually' in periodic:
            lines.append("**연간**")
            for item in periodic['annually']:
                lines.append(f"  - {item}")
            lines.append("")
        if 'on_change' in periodic:
            lines.append("**변경 시**")
            for item in periodic['on_change']:
                lines.append(f"  - {item}")
            lines.append("")
        lines.append("---")
        lines.append("")

    # 업종별 추가 검토 (privacy)
    sector_notes = data.get('sector_specific_notes', [])
    if sector_notes:
        lines.append("## 🏢 업종별 추가 검토")
        lines.append("")
        for sn in sector_notes:
            lines.append(f"**{sn.get('sector', '')}**: {sn.get('additional', '')}")
        lines.append("")
        lines.append("---")
        lines.append("")

    # 연관 법령 맵 (fair_trade)
    laws_map = data.get('related_laws_map', [])
    if laws_map:
        lines.append("## 📚 상황별 연관 법령")
        lines.append("")
        for lm in laws_map:
            lines.append(f"**{lm.get('context', '')}**")
            for law in lm.get('laws', []):
                lines.append(f"  - {law}")
            if lm.get('note'):
                lines.append(f"  - 💡 {lm['note']}")
            lines.append("")
        lines.append("---")
        lines.append("")

    # 제재 동향 확인 팁 (fair_trade)
    enforcement_tips = data.get('enforcement_check_tips', [])
    if enforcement_tips:
        lines.append("## 🔍 제재 동향 확인 팁")
        lines.append("")
        for tip in enforcement_tips:
            lines.append(f"- {tip}")
        lines.append("")
        lines.append("---")
        lines.append("")

    # 적용 대상 (scope) - 중대재해처벌법 등
    scope_items = data.get('scope', [])
    if scope_items:
        lines.append("## 📋 적용 대상 판단")
        lines.append("")
        for item in scope_items:
            if not isinstance(item, dict):
                continue
            task = item.get('task', '')
            if not task:
                continue
            lines.append(f"### {task}")
            for cp in item.get('check_points', []):
                if isinstance(cp, str):
                    lines.append(f"- [ ] {cp}")
            notes = item.get('notes', '')
            if notes:
                for note_line in str(notes).strip().split('\n'):
                    lines.append(f"> {note_line.strip()}")
            lines.append("")
        lines.append("---")
        lines.append("")

    # 처벌 규정 (penalties) - 중대재해처벌법 등
    penalties = data.get('penalties', {})
    if penalties:
        lines.append(f"## ⚖️ {penalties.get('title', '처벌 규정')}")
        lines.append("")
        individual = penalties.get('individual', {})
        if individual:
            lines.append("**개인 (경영책임자 등)**")
            for key, val in individual.items():
                if isinstance(val, dict):
                    lines.append(f"- {val.get('description', key)}: {val.get('punishment', '')}")
            lines.append("")
        corporation = penalties.get('corporation', {})
        if corporation:
            lines.append("**법인**")
            for key, val in corporation.items():
                if isinstance(val, dict):
                    lines.append(f"- {val.get('description', key)}: {val.get('punishment', '')}")
            lines.append("")
        civil = penalties.get('civil', {})
        if civil:
            lines.append(f"**민사**: {civil.get('description', '')} - {civil.get('punishment', '')}")
            lines.append("")
        lines.append("---")
        lines.append("")

    # 계약 유형별 검토 (contract_types) - 계약서 검토 가이드
    contract_types = data.get('contract_types', [])
    if contract_types:
        lines.append("## 📝 계약 유형별 검토 포인트")
        lines.append("")
        for ct in contract_types:
            if not isinstance(ct, dict):
                continue
            type_name = ct.get('type_name', '')
            if not type_name:
                continue
            lines.append(f"### {type_name}")
            lines.append("")
            for issue in ct.get('key_issues', []):
                if not isinstance(issue, dict):
                    continue
                issue_name = issue.get('issue', '')
                if issue_name:
                    lines.append(f"**{issue_name}**")
                for cp in issue.get('check_points', []):
                    if isinstance(cp, str):
                        lines.append(f"- [ ] {cp}")
                why = issue.get('why_it_matters', '')
                if why:
                    for line in str(why).strip().split('\n'):
                        lines.append(f"> {line.strip()}")
                lines.append("")
            lines.append("---")
            lines.append("")

    # 공통 위험 조항 (common_risk_clauses) - 계약서 검토 가이드
    risk_clauses = data.get('common_risk_clauses', [])
    if risk_clauses:
        lines.append("## ⚠️ 공통 위험 조항")
        lines.append("")
        for rc in risk_clauses:
            if not isinstance(rc, dict):
                continue
            risk_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(rc.get('risk_level', 'medium'), '⚪')
            clause_name = rc.get('clause', '')
            if not clause_name:
                continue
            lines.append(f"### {clause_name} {risk_emoji}")
            for cp in rc.get('check_points', []):
                if isinstance(cp, str):
                    lines.append(f"- [ ] {cp}")
            laws = rc.get('laws', [])
            if laws:
                lines.append("**관련 법령**:")
                for law in laws:
                    if not isinstance(law, dict):
                        continue
                    law_name = law.get('name', '')
                    if not law_name:
                        continue
                    articles = law.get('articles', [])
                    link = _generate_law_link(law_name)
                    if articles:
                        articles_str = ", ".join(str(a) for a in articles if a)
                        lines.append(f"- [{law_name}]({link}): {articles_str}")
                    else:
                        lines.append(f"- [{law_name}]({link})")
            lines.append("")
        lines.append("---")
        lines.append("")

    # 실사 영역 (due_diligence_areas) - 투자 실사 가이드
    dd_areas = data.get('due_diligence_areas', [])
    if dd_areas:
        lines.append("## 🔍 법률실사 영역")
        lines.append("")
        for area in dd_areas:
            if not isinstance(area, dict):
                continue
            area_name = area.get('area_name', '')
            if not area_name:
                continue
            lines.append(f"### {area_name}")
            lines.append("")
            for item in area.get('items', []):
                if not isinstance(item, dict):
                    continue
                item_name = item.get('item', '')
                if item_name:
                    lines.append(f"**{item_name}**")
                for cp in item.get('check_points', []):
                    if isinstance(cp, str):
                        lines.append(f"- [ ] {cp}")
                docs = item.get('documents', [])
                if docs:
                    doc_list = [str(d) for d in docs if d]
                    if doc_list:
                        lines.append("*필요 서류*: " + ", ".join(doc_list))
                why = item.get('why_it_matters', '')
                if why:
                    for line in str(why).strip().split('\n'):
                        lines.append(f"> {line.strip()}")
                lines.append("")
            lines.append("---")
            lines.append("")

    # 투자계약 주요 조항 (investment_contract_terms)
    inv_terms = data.get('investment_contract_terms', {})
    if inv_terms and isinstance(inv_terms, dict):
        lines.append(f"## 💰 {inv_terms.get('title', '투자계약 주요 조항')}")
        lines.append("")
        note = inv_terms.get('note', '')
        if note:
            for line in str(note).strip().split('\n'):
                lines.append(f"> {line.strip()}")
            lines.append("")
        for term in inv_terms.get('terms', []):
            if not isinstance(term, dict):
                continue
            term_name = term.get('term', '')
            if term_name:
                lines.append(f"**{term_name}**")
            for cp in term.get('check_points', []):
                if isinstance(cp, str):
                    lines.append(f"- [ ] {cp}")
            why = term.get('why_it_matters', '')
            if why:
                for line in str(why).strip().split('\n'):
                    lines.append(f"> {line.strip()}")
            lines.append("")
        lines.append("---")
        lines.append("")

    # 규모별 적용 (scale_based_requirements) - 노동법
    scale_req = data.get('scale_based_requirements', {})
    if scale_req and isinstance(scale_req, dict):
        lines.append("## 📊 규모별 적용 정리")
        lines.append("")
        for key, val in scale_req.items():
            if isinstance(val, dict):
                lines.append(f"**{val.get('name', key)}**")
                excluded = val.get('excluded', [])
                if excluded:
                    lines.append("*적용 제외*:")
                    for item in excluded:
                        if isinstance(item, str):
                            lines.append(f"  - ❌ {item}")
                applied = val.get('applied', [])
                if applied:
                    lines.append("*적용*:")
                    for item in applied:
                        if isinstance(item, str):
                            lines.append(f"  - ✅ {item}")
                additional = val.get('additional', [])
                if additional:
                    lines.append("*추가 의무*:")
                    for item in additional:
                        if isinstance(item, str):
                            lines.append(f"  - ➕ {item}")
                lines.append("")
        lines.append("---")
        lines.append("")

    # 약관규제법 참고 (unfair_terms_reference)
    unfair_ref = data.get('unfair_terms_reference', {})
    if unfair_ref and isinstance(unfair_ref, dict):
        lines.append(f"## 📖 {unfair_ref.get('title', '약관규제법 참고')}")
        lines.append("")
        for law in unfair_ref.get('laws', []):
            if not isinstance(law, dict):
                continue
            law_name = law.get('name', '')
            if not law_name:
                continue
            link = _generate_law_link(law_name)
            lines.append(f"**[{law_name}]({link})**")
            for art in law.get('articles', []):
                if isinstance(art, str):
                    lines.append(f"- {art}")
        note = unfair_ref.get('note', '')
        if note:
            lines.append("")
            for line in str(note).strip().split('\n'):
                lines.append(f"> {line.strip()}")
        lines.append("")
        lines.append("---")
        lines.append("")

    # 실사에서 제외 (not_covered for DD)
    not_covered_dd = data.get('not_covered', {})
    if isinstance(not_covered_dd, dict) and not_covered_dd.get('title'):
        lines.append(f"## ⚠️ {not_covered_dd.get('title', '범위 외')}")
        lines.append("")
        for item in not_covered_dd.get('items', []):
            if not isinstance(item, dict):
                continue
            area = item.get('area', '')
            note = item.get('note', '')
            if area:
                lines.append(f"- **{area}**: {note}")
        lines.append("")
        lines.append("---")
        lines.append("")

    # 면책 고지
    disclaimer = data.get('disclaimer', '')
    if disclaimer:
        lines.append(f"> ⚠️ **면책**: {disclaimer.strip()}")
    else:
        lines.append("> ⚠️ **참고**: 이 문서는 일반적인 정보 제공 목적이며,")
        lines.append("> 구체적인 법률 문제는 변호사와 상담하시기 바랍니다.")

    output = "\n".join(lines)

    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"저장됨: {output_file}")
    else:
        print(output)

    return data


# ─────────────────────────────────────────────────────────
# 법정 의무 캘린더 (Compliance Calendar)
# ─────────────────────────────────────────────────────────

def load_calendar():
    """법정 의무 캘린더 YAML 로드"""
    if not CALENDAR_PATH.exists():
        print(f"ERROR: 캘린더 파일을 찾을 수 없습니다: {CALENDAR_PATH}", file=sys.stderr)
        return None

    try:
        with open(CALENDAR_PATH, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"ERROR: YAML 파싱 오류: {CALENDAR_PATH}", file=sys.stderr)
        print(f"  상세: {e}", file=sys.stderr)
        return None
    except (PermissionError, OSError) as e:
        print(f"ERROR: 파일 읽기 실패: {e}", file=sys.stderr)
        return None

    if data is None:
        print(f"ERROR: 캘린더 파일이 비어 있습니다: {CALENDAR_PATH}", file=sys.stderr)
        return None

    return data


def get_upcoming_obligations(days: int = 30, filter_type: str = None):
    """다가오는 법정 의무 목록 반환

    Args:
        days: 앞으로 N일 이내의 의무
        filter_type: 필터 (all, listed, large, sme, corp)

    Returns:
        tuple: (list of obligations, skipped_count)
    """
    data = load_calendar()
    if not data:
        return [], 0

    today = datetime.now()
    current_year = today.year
    current_month = today.month

    upcoming = []
    skipped_count = 0

    # 연간 의무 처리
    for item in data.get('annual', []):
        deadline_month = item.get('deadline_month')
        deadline_day = item.get('deadline_day', 1)

        if deadline_month:
            # 올해 또는 내년 기준으로 마감일 계산
            try:
                deadline = datetime(current_year, deadline_month, deadline_day)
                if deadline < today:
                    # 이미 지났으면 내년으로
                    deadline = datetime(current_year + 1, deadline_month, deadline_day)
            except ValueError as e:
                print(f"WARNING: 날짜 오류로 '{item.get('name')}' 건너뜀 ({deadline_month}/{deadline_day}): {e}",
                      file=sys.stderr)
                skipped_count += 1
                continue

            days_until = (deadline - today).days
            if 0 <= days_until <= days:
                # 필터 적용
                if filter_type and filter_type != 'all':
                    applies_to = item.get('applies_to', {})
                    company_types = applies_to.get('company_type', ['all'])
                    if filter_type not in company_types and 'all' not in company_types:
                        continue

                upcoming.append({
                    'type': 'annual',
                    'id': item.get('id'),
                    'name': item.get('name'),
                    'description': item.get('description'),
                    'law': item.get('law'),
                    'deadline': deadline.strftime('%Y-%m-%d'),
                    'days_until': days_until,
                    'priority': item.get('priority', 'medium'),
                    'penalty': item.get('penalty'),
                })

    # 분기 의무 처리 (occurrences 사용)
    for item in data.get('quarterly', []):
        for occ in item.get('occurrences', []):
            occ_month = occ.get('month')
            occ_day = occ.get('day', 1)

            if occ_month:
                try:
                    deadline = datetime(current_year, occ_month, occ_day)
                    if deadline < today:
                        deadline = datetime(current_year + 1, occ_month, occ_day)
                except ValueError as e:
                    print(f"WARNING: 날짜 오류로 '{item.get('name')}' 건너뜀 ({occ_month}/{occ_day}): {e}",
                          file=sys.stderr)
                    skipped_count += 1
                    continue

                days_until = (deadline - today).days
                if 0 <= days_until <= days:
                    if filter_type and filter_type != 'all':
                        applies_to = item.get('applies_to', {})
                        company_types = applies_to.get('company_type', ['all'])
                        if filter_type not in company_types and 'all' not in company_types:
                            continue

                    upcoming.append({
                        'type': 'quarterly',
                        'id': item.get('id'),
                        'name': f"{item.get('name')} ({occ.get('label', '')})",
                        'description': item.get('description'),
                        'law': item.get('law'),
                        'deadline': deadline.strftime('%Y-%m-%d'),
                        'days_until': days_until,
                        'priority': item.get('priority', 'medium'),
                        'penalty': item.get('penalty'),
                    })

    # 월별 의무 처리
    for item in data.get('monthly', []):
        deadline_day = item.get('deadline_day', 10)

        # 이번 달 또는 다음 달 (2월 등 짧은 달은 마지막 날로 조정)
        target_year = current_year
        target_month = current_month

        # 해당 월의 마지막 날 확인
        last_day_of_month = calendar.monthrange(target_year, target_month)[1]
        actual_day = min(deadline_day, last_day_of_month)
        deadline = datetime(target_year, target_month, actual_day)

        if deadline < today:
            # 이번 달 지났으면 다음 달
            target_month += 1
            if target_month > 12:
                target_month = 1
                target_year += 1
            last_day_of_month = calendar.monthrange(target_year, target_month)[1]
            actual_day = min(deadline_day, last_day_of_month)
            deadline = datetime(target_year, target_month, actual_day)

        days_until = (deadline - today).days
        if 0 <= days_until <= days:
            if filter_type and filter_type != 'all':
                applies_to = item.get('applies_to', {})
                company_types = applies_to.get('company_type', ['all'])
                if filter_type not in company_types and 'all' not in company_types:
                    continue

            upcoming.append({
                'type': 'monthly',
                'id': item.get('id'),
                'name': item.get('name'),
                'description': item.get('description'),
                'law': item.get('law'),
                'deadline': deadline.strftime('%Y-%m-%d'),
                'days_until': days_until,
                'priority': item.get('priority', 'medium'),
                'penalty': item.get('penalty'),
            })

    # 마감일 순 정렬
    upcoming.sort(key=lambda x: x['days_until'])

    return upcoming, skipped_count


def show_calendar(days: int = 30, filter_type: str = None, output_format: str = 'text'):
    """법정 의무 캘린더 출력

    Args:
        days: 앞으로 N일 이내의 의무 표시
        filter_type: 회사 유형 필터
        output_format: 출력 형식 (text, json)
    """
    data = load_calendar()
    if not data:
        return

    upcoming, skipped_count = get_upcoming_obligations(days, filter_type)

    if output_format == 'json':
        result = {'upcoming': upcoming, 'total': len(upcoming)}
        if skipped_count > 0:
            result['skipped_count'] = skipped_count
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # 헤더
    today_str = datetime.now().strftime('%Y-%m-%d')
    print(f"\n📅 법정 의무 캘린더 (기준일: {today_str})")
    print(f"   앞으로 {days}일 내 마감 의무")
    if filter_type:
        print(f"   필터: {filter_type}")
    print("=" * 60)

    if not upcoming:
        print("\n✅ 해당 기간 내 마감 의무가 없습니다.")
        return

    # 우선순위별 이모지
    priority_emoji = {
        'critical': '🔴',
        'high': '🟠',
        'medium': '🟡',
        'low': '🟢',
    }

    for item in upcoming:
        emoji = priority_emoji.get(item['priority'], '⚪')
        days_text = f"D-{item['days_until']}" if item['days_until'] > 0 else "📢 오늘!"

        print(f"\n{emoji} [{days_text}] {item['name']}")
        print(f"   마감: {item['deadline']}")
        print(f"   근거: {item['law']}")
        if item.get('penalty'):
            print(f"   벌칙: {item['penalty']}")

    print("\n" + "=" * 60)
    print(f"총 {len(upcoming)}건")

    # 건너뛴 항목 경고
    if skipped_count > 0:
        print(f"\n⚠️  WARNING: {skipped_count}건의 의무가 데이터 오류로 건너뛰어졌습니다.", file=sys.stderr)

    # 면책 고지
    disclaimer = data.get('disclaimer', '')
    if disclaimer:
        print(f"\n⚠️  {disclaimer[:100]}...")


def show_calendar_all(output_format: str = 'text'):
    """전체 법정 의무 목록 출력"""
    data = load_calendar()
    if not data:
        return

    if output_format == 'json':
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    print(f"\n📅 {data.get('name', '법정 의무 캘린더')}")
    print(f"   {data.get('description', '')}")
    print(f"   마지막 업데이트: {data.get('last_updated', 'N/A')}")
    print("=" * 60)

    # 연간 의무
    annual = data.get('annual', [])
    if annual:
        print(f"\n📆 연간 의무 ({len(annual)}건)")
        print("-" * 40)
        for item in annual:
            print(f"  • {item.get('name')}")
            print(f"    기한: {item.get('deadline_rule')}")
            print(f"    근거: {item.get('law')}")

    # 분기 의무
    quarterly = data.get('quarterly', [])
    if quarterly:
        print(f"\n📆 분기 의무 ({len(quarterly)}건)")
        print("-" * 40)
        for item in quarterly:
            print(f"  • {item.get('name')}")
            print(f"    기한: {item.get('deadline_rule')}")

    # 월별 의무
    monthly = data.get('monthly', [])
    if monthly:
        print(f"\n📆 월별 의무 ({len(monthly)}건)")
        print("-" * 40)
        for item in monthly:
            print(f"  • {item.get('name')}")
            print(f"    기한: 매월 {item.get('deadline_day')}일")

    # 수시 의무
    event_driven = data.get('event_driven', [])
    if event_driven:
        print(f"\n📆 수시 의무 ({len(event_driven)}건)")
        print("-" * 40)
        for item in event_driven:
            print(f"  • {item.get('name')}")
            print(f"    트리거: {item.get('trigger')}")
            print(f"    기한: {item.get('deadline_rule')}")

    total = len(annual) + len(quarterly) + len(monthly) + len(event_driven)
    print(f"\n총 {total}건")


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
    search_parser.add_argument('--format', '-f', default='text', choices=['text', 'json'],
                               help='출력 형식 (text: 텍스트, json: JSON)')

    # cases 명령 (판례 전용)
    cases_parser = subparsers.add_parser('cases', help='판례 검색')
    cases_parser.add_argument('query', help='검색어')
    cases_parser.add_argument('--court', help='법원 필터 (대법원, 고등, 지방)')
    cases_parser.add_argument('--from', dest='from_date', help='검색 시작일 (YYYYMMDD)')
    cases_parser.add_argument('--display', type=int, default=20, help='결과 개수')
    cases_parser.add_argument('--page', type=int, default=1, help='페이지 번호')
    cases_parser.add_argument('--format', '-f', default='text', choices=['text', 'json'],
                              help='출력 형식 (text: 텍스트, json: JSON)')

    # exact 명령 (정확한 법령명 검색)
    exact_parser = subparsers.add_parser('exact', help='정확한 법령명 검색 (예: 상법, 민법)')
    exact_parser.add_argument('name', help='정확한 법령명')
    exact_parser.add_argument('--with-admrul', action='store_true',
                              help='관련 행정규칙(고시/훈령/예규)도 함께 검색')
    exact_parser.add_argument('--format', '-f', default='text', choices=['text', 'json'],
                              help='출력 형식 (text: 텍스트, json: JSON)')

    # fetch 명령
    fetch_parser = subparsers.add_parser('fetch', help='법령/판례/행정규칙 다운로드')
    fetch_parser.add_argument('--id', help='법령/판례/행정규칙 ID')
    fetch_parser.add_argument('--name', help='법령명')
    fetch_parser.add_argument('--case', help='판례 사건번호 (예: 2022다12345)')
    fetch_parser.add_argument('--type', default='law',
                              choices=['law', 'admrul', 'prec', 'ordin', 'expc', 'detc'],
                              help='다운로드 대상 (law: 법령, admrul: 행정규칙, prec: 판례 등)')
    fetch_parser.add_argument('--with-decree', action='store_true',
                              help='시행령/시행규칙도 함께 다운로드')
    fetch_parser.add_argument('--force', action='store_true',
                              help='캐시 무시하고 강제 다운로드')

    # recent 명령
    recent_parser = subparsers.add_parser('recent', help='최근 개정 법령')
    recent_parser.add_argument('--days', type=int, default=30, help='최근 N일')
    recent_parser.add_argument('--from', dest='from_date', help='시작일 (YYYYMMDD)')
    recent_parser.add_argument('--to', dest='to_date', help='종료일 (YYYYMMDD)')
    recent_parser.add_argument('--date-type', choices=['ef', 'anc'], default='ef',
                               help='날짜 기준 (ef: 시행일, anc: 공포일)')
    recent_parser.add_argument('--format', '-f', default='text', choices=['text', 'json'],
                               help='출력 형식 (text: 텍스트, json: JSON)')

    # checklist 명령
    checklist_parser = subparsers.add_parser('checklist', help='법적 체크리스트 조회')
    checklist_subparsers = checklist_parser.add_subparsers(dest='checklist_command', help='체크리스트 명령')

    # checklist list
    checklist_list_parser = checklist_subparsers.add_parser('list', help='사용 가능한 체크리스트 목록')

    # checklist show
    checklist_show_parser = checklist_subparsers.add_parser('show', help='체크리스트 출력')
    checklist_show_parser.add_argument('name', help='체크리스트 이름 (예: startup, privacy_compliance, fair_trade)')
    checklist_show_parser.add_argument('--output', '-o', help='출력 파일 경로 (예: checklist.md)')
    checklist_show_parser.add_argument('--format', '-f', default='markdown', choices=['markdown', 'json'],
                                       help='출력 형식 (markdown, json)')

    # calendar 명령 (법정 의무 캘린더)
    calendar_parser = subparsers.add_parser('calendar', help='법정 의무 캘린더 조회')
    calendar_subparsers = calendar_parser.add_subparsers(dest='calendar_command', help='캘린더 명령')

    # calendar upcoming (기본)
    calendar_upcoming_parser = calendar_subparsers.add_parser('upcoming', help='다가오는 법정 의무')
    calendar_upcoming_parser.add_argument('--days', type=int, default=30, help='앞으로 N일 내 (기본: 30)')
    calendar_upcoming_parser.add_argument('--filter', dest='filter_type',
                                          choices=['all', 'corp', 'listed', 'large', 'sme'],
                                          help='회사 유형 필터')
    calendar_upcoming_parser.add_argument('--format', '-f', default='text', choices=['text', 'json'],
                                          help='출력 형식')

    # calendar list (전체 목록)
    calendar_list_parser = calendar_subparsers.add_parser('list', help='전체 법정 의무 목록')
    calendar_list_parser.add_argument('--format', '-f', default='text', choices=['text', 'json'],
                                      help='출력 형식')

    args = parser.parse_args()

    if args.command == 'search':
        search_laws(args.query, target=args.type, display=args.display, page=args.page,
                    sort=args.sort, output_format=args.format)
    elif args.command == 'exact':
        search_exact_law(args.name, with_admrul=args.with_admrul, output_format=args.format)
    elif args.command == 'cases':
        search_cases(args.query, court=args.court, from_date=args.from_date,
                     display=args.display, page=args.page, output_format=args.format)
    elif args.command == 'fetch':
        if args.case:
            fetch_case_by_number(args.case)
        elif args.id:
            fetch_law_by_id(args.id, force=args.force, target=args.type)
        elif args.name:
            fetch_law_by_name(args.name, args.with_decree, args.force)
        else:
            print("Error: --id, --name, 또는 --case 중 하나를 지정하세요.", file=sys.stderr)
            sys.exit(1)
    elif args.command == 'recent':
        get_recent_laws(args.days, args.from_date, args.to_date, date_type=args.date_type, output_format=args.format)
    elif args.command == 'checklist':
        if args.checklist_command == 'list':
            list_checklists()
        elif args.checklist_command == 'show':
            show_checklist(args.name, output_file=args.output, output_format=args.format)
        else:
            checklist_parser.print_help()
    elif args.command == 'calendar':
        if args.calendar_command == 'upcoming':
            show_calendar(days=args.days, filter_type=args.filter_type, output_format=args.format)
        elif args.calendar_command == 'list':
            show_calendar_all(output_format=args.format)
        else:
            # 기본: upcoming 30일
            show_calendar(days=30)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
