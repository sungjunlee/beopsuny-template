#!/usr/bin/env python3
"""
permits.yaml 생성기

시드 데이터(seed_data.yaml)에서 최종 permits.yaml을 생성합니다.

Usage:
    python generate_permits.py
    python generate_permits.py --output /custom/path/permits.yaml
    python generate_permits.py --dry-run  # 실제 저장 없이 출력만

Exit codes:
    0: 성공
    1: 시드 데이터 없음
    2: 에러 발생
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
import yaml

# 경로 설정
SCRIPT_DIR = Path(__file__).parent
DEFAULT_OUTPUT = SCRIPT_DIR / "../../.claude/skills/beopsuny/assets/permits.yaml"
SEED_DATA_PATH = SCRIPT_DIR / "seed_data.yaml"

# YAML 헤더 (주석)
YAML_HEADER = """# ============================================================
# 기업 허가/신고 인덱스
# Business Permits & Registrations Index
# ============================================================
# 기업 설립 및 운영에 필요한 주요 허가/인가/등록/신고 정보
#
# 용도:
#   1. 업종별 필요 인허가 조회 (fetch_law.py permits)
#   2. 체크리스트 자동 생성
#   3. 근거법령 크로스레퍼런스
#
# 데이터 출처:
#   - 정부24 민원안내 (gov.kr)
#   - 찾기쉬운법령 (easylaw.go.kr)
#   - 수동 큐레이션 (tools/permits/seed_data.yaml)
#
# 주의:
#   - 법령 개정으로 요건/서류 변경 가능
#   - 분기별 확인 권장 (GitHub Actions 자동화)

"""


def load_seed_data() -> dict:
    """시드 데이터 로드"""
    if not SEED_DATA_PATH.exists():
        print(f"Error: {SEED_DATA_PATH} not found", file=sys.stderr)
        sys.exit(1)

    try:
        with open(SEED_DATA_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        print(f"Error parsing seed data: {e}", file=sys.stderr)
        sys.exit(2)
    except (OSError, UnicodeDecodeError) as e:
        print(f"Error reading seed data file: {e}", file=sys.stderr)
        sys.exit(2)


def get_last_verified(item: dict) -> str:
    """sources에서 last_verified 추출, 없으면 오늘 날짜 반환"""
    sources = item.get("sources")
    if sources and isinstance(sources, list) and len(sources) > 0:
        first_source = sources[0]
        if isinstance(first_source, dict) and "accessed" in first_source:
            return first_source["accessed"]
    return datetime.now().strftime("%Y-%m-%d")


def transform_item(item: dict) -> dict:
    """시드 데이터 항목을 최종 스키마로 변환"""
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "type": item.get("type"),
        "category": item.get("category"),
        "description": item.get("description"),
        "law": item.get("law"),
        "authority": item.get("authority"),
        "processing": item.get("processing"),
        "fees": item.get("fees"),
        "documents": item.get("documents", []),
        "requirements": item.get("requirements", []),
        "penalty": item.get("penalty", []),
        "related_checklists": item.get("related_checklists", []),
        "priority": item.get("priority", "medium"),
        "gov24_url": item.get("gov24_url"),
        "sources": item.get("sources", []),
        "last_verified": get_last_verified(item),
        "notes": item.get("notes"),
    }


def generate_permits_yaml(seed_data: dict) -> dict:
    """최종 permits.yaml 구조 생성"""
    today = datetime.now().strftime("%Y-%m-%d")

    # 다음 분기 계산
    now = datetime.now()
    next_quarter_month = ((now.month - 1) // 3 + 1) * 3 + 1
    if next_quarter_month > 12:
        next_quarter_month = 1
        next_review = f"{now.year + 1}-{next_quarter_month:02d}"
    else:
        next_review = f"{now.year}-{next_quarter_month:02d}"

    items = [transform_item(item) for item in seed_data.get("items", [])]

    return {
        "name": "기업 허가/신고 인덱스",
        "description": "업종별 허가/인가/등록/신고 요건 및 근거법령",
        "type": "permits",
        "category": "기업법무",
        "last_updated": today,
        "maintenance": {
            "review_cycle": "quarterly",
            "next_review": next_review,
            "volatile_items": [
                "수수료 금액",
                "구비서류 목록",
                "자본금 요건",
            ],
            "data_source": {
                "primary": "수동 큐레이션 (tools/permits/seed_data.yaml)",
                "secondary": "gov.kr (정부24)",
            },
            "note": "분기별 법령 개정 확인 권장",
            "changelog": [
                {
                    "date": today,
                    "changes": f"초기 버전 생성 (IT/스타트업 중심 {len(items)}개)",
                }
            ],
        },
        "categories": seed_data.get("categories", []),
        "permit_types": seed_data.get("permit_types", []),
        "items": items,
        "disclaimer": (
            "이 데이터는 정부24(gov.kr) 및 각 부처 공식 자료를 기반으로 합니다.\n"
            "법령 개정으로 최신 정보와 다를 수 있으므로 중요한 결정 전\n"
            "관할 기관 또는 전문가와 확인하세요."
        ),
    }


def main():
    parser = argparse.ArgumentParser(
        description="시드 데이터에서 permits.yaml 생성"
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT.resolve()),
        help="출력 파일 경로 (기본: assets/permits.yaml)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 저장 없이 stdout에 출력",
    )
    args = parser.parse_args()

    # 시드 데이터 로드
    seed_data = load_seed_data()
    print(f"Loaded {len(seed_data.get('items', []))} items from seed data", file=sys.stderr)

    # permits.yaml 생성
    permits_data = generate_permits_yaml(seed_data)

    # YAML 문자열 생성
    yaml_content = YAML_HEADER + yaml.dump(
        permits_data,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=120,
    )

    if args.dry_run:
        print(yaml_content)
    else:
        output_path = Path(args.output)

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"Error creating output directory {output_path.parent}: {e}", file=sys.stderr)
            sys.exit(2)

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(yaml_content)
        except OSError as e:
            print(f"Error writing to {output_path}: {e}", file=sys.stderr)
            sys.exit(2)

        print(f"Generated {output_path} with {len(permits_data['items'])} permits", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
