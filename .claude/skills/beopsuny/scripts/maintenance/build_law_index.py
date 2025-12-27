#!/usr/bin/env python3
"""
역 인덱스 생성기 - 법령명 → YAML 파일 매핑

법령이 개정되면 어떤 YAML 파일이 영향을 받는지 식별하기 위한 인덱스를 생성합니다.

Usage:
    python build_law_index.py              # 인덱스 생성 및 출력
    python build_law_index.py --json       # JSON 형식으로 출력
    python build_law_index.py --save       # data/law_to_files.json으로 저장
    python build_law_index.py --lookup "개인정보보호법"  # 특정 법령 조회
"""

import argparse
import json
import sys
from pathlib import Path

import yaml

# 경로 설정
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent.parent
ASSETS_DIR = SKILL_DIR / "assets"
CHECKLISTS_DIR = ASSETS_DIR / "checklists"
DATA_DIR = SKILL_DIR / "data"

# 인덱스 저장 경로
INDEX_OUTPUT_PATH = DATA_DIR / "law_to_files.json"

# 정규화된 법령명 목록 (law_index.yaml 기준)
KNOWN_LAWS = None


def load_known_laws():
    """law_index.yaml에서 알려진 법령명 목록 로드"""
    global KNOWN_LAWS
    if KNOWN_LAWS is not None:
        return KNOWN_LAWS

    law_index_path = ASSETS_DIR / "law_index.yaml"
    if not law_index_path.exists():
        KNOWN_LAWS = set()
        return KNOWN_LAWS

    try:
        with open(law_index_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except (yaml.YAMLError, OSError, UnicodeDecodeError) as e:
        print(f"Warning: Cannot read {law_index_path}: {e}", file=sys.stderr)
        KNOWN_LAWS = set()
        return KNOWN_LAWS

    KNOWN_LAWS = set(data.get("major_laws", {}).keys())
    return KNOWN_LAWS


def normalize_law_name(name: str) -> str:
    """법령명 정규화 (약칭 → 정식명)"""
    # 일반적인 약칭 매핑
    aliases = {
        "개보법": "개인정보보호법",
        "정통망법": "정보통신망법",
        "근기법": "근로기준법",
        "산안법": "산업안전보건법",
        "공정거래법": "독점규제및공정거래에관한법률",
        "자본시장법": "자본시장과금융투자업에관한법률",
    }
    return aliases.get(name, name)


def extract_law_names_from_text(text: str) -> set:
    """텍스트에서 법령명 추출"""
    laws = set()
    known = load_known_laws()

    # 알려진 법령명 직접 매칭 (우선)
    for law_name in known:
        if law_name in text:
            laws.add(law_name)

    return laws


def extract_laws_from_yaml(filepath: Path) -> dict:
    """
    YAML 파일에서 법령 참조 추출

    Returns:
        {
            "법령명": ["항목ID1", "항목ID2", ...],
            ...
        }
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except (yaml.YAMLError, OSError, UnicodeDecodeError) as e:
        print(f"Warning: Cannot read {filepath}: {e}", file=sys.stderr)
        return {}

    laws = {}
    known = load_known_laws()

    def add_law(law_name: str, item_id: str = None):
        # 정규화
        normalized = normalize_law_name(law_name.strip())
        # 알려진 법령인지 확인 (부분 매칭)
        matched = None
        for known_law in known:
            if known_law in normalized or normalized in known_law:
                matched = known_law
                break
        if matched:
            if matched not in laws:
                laws[matched] = []
            if item_id and item_id not in laws[matched]:
                laws[matched].append(item_id)

    def extract_from_string(text: str, item_id: str = None):
        """문자열에서 법령명 추출"""
        for law_name in known:
            if law_name in text:
                add_law(law_name, item_id)

    def process_items(items: list, id_field: str = "id"):
        """항목 리스트 처리"""
        for item in items:
            if not isinstance(item, dict):
                continue

            item_id = item.get(id_field, "")

            # law 필드 (문자열)
            if "law" in item:
                extract_from_string(str(item["law"]), item_id)

            # laws 필드 (리스트)
            if "laws" in item and isinstance(item["laws"], list):
                for law_ref in item["laws"]:
                    if isinstance(law_ref, dict) and "name" in law_ref:
                        add_law(law_ref["name"], item_id)
                    elif isinstance(law_ref, str):
                        extract_from_string(law_ref, item_id)

            # notes 필드 (텍스트 내 법령 언급)
            if "notes" in item and isinstance(item["notes"], str):
                extract_from_string(item["notes"], item_id)

    # compliance_calendar.yaml 구조
    for section in ["annual", "quarterly", "monthly", "event_driven"]:
        if section in data and isinstance(data[section], list):
            process_items(data[section])

    # checklists 구조
    if "items" in data and isinstance(data["items"], list):
        process_items(data["items"])

    # clause_references.yaml 구조
    if "categories" in data and isinstance(data["categories"], list):
        for category in data["categories"]:
            if "clauses" in category and isinstance(category["clauses"], list):
                for clause in category["clauses"]:
                    if isinstance(clause, dict):
                        clause_id = clause.get("id", "")
                        if "legal_basis" in clause:
                            extract_from_string(str(clause["legal_basis"]), clause_id)
                        if "laws" in clause and isinstance(clause["laws"], list):
                            for law in clause["laws"]:
                                if isinstance(law, str):
                                    extract_from_string(law, clause_id)

    return laws


def build_reverse_index() -> dict:
    """
    모든 YAML 파일을 스캔하여 역 인덱스 생성

    Returns:
        {
            "법령명": {
                "files": [
                    {"path": "상대경로", "items": ["item-id-1", ...]},
                    ...
                ]
            },
            ...
        }
    """
    index = {}

    # 스캔할 YAML 파일 목록
    yaml_files = [
        ASSETS_DIR / "compliance_calendar.yaml",
        ASSETS_DIR / "clause_references.yaml",
    ]
    yaml_files.extend(CHECKLISTS_DIR.glob("*.yaml"))

    for filepath in yaml_files:
        if not filepath.exists():
            continue

        rel_path = filepath.relative_to(ASSETS_DIR)
        laws = extract_laws_from_yaml(filepath)

        for law_name, item_ids in laws.items():
            if law_name not in index:
                index[law_name] = {"files": []}

            index[law_name]["files"].append({
                "path": str(rel_path),
                "items": item_ids,
            })

    return index


def main():
    parser = argparse.ArgumentParser(description="법령 → YAML 파일 역 인덱스 생성")
    parser.add_argument("--save", action="store_true", help="인덱스를 JSON 파일로 저장")
    parser.add_argument("--lookup", type=str, help="특정 법령 조회")
    parser.add_argument("--json", action="store_true", help="JSON 형식으로 출력")
    args = parser.parse_args()

    index = build_reverse_index()

    if args.lookup:
        # 특정 법령 조회
        law_name = args.lookup
        if law_name in index:
            files = index[law_name]["files"]
            if args.json:
                print(json.dumps({law_name: index[law_name]}, ensure_ascii=False, indent=2))
            else:
                print(f"\n📚 '{law_name}' 참조 파일:\n")
                for file_info in files:
                    path = file_info["path"]
                    items = file_info["items"]
                    if items:
                        print(f"  📄 {path}")
                        for item_id in items:
                            print(f"      └─ {item_id}")
                    else:
                        print(f"  📄 {path}")
        else:
            print(f"'{law_name}'을(를) 참조하는 파일이 없습니다.", file=sys.stderr)
            sys.exit(1)
        return

    if args.save:
        # 파일로 저장
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(INDEX_OUTPUT_PATH, "w", encoding="utf-8") as f:
                json.dump(index, f, ensure_ascii=False, indent=2)
            print(f"✅ 인덱스 저장됨: {INDEX_OUTPUT_PATH}")
            print(f"   총 {len(index)}개 법령 인덱싱")
        except OSError as e:
            print(f"Error: 인덱스 저장 실패: {e}", file=sys.stderr)
            sys.exit(2)
        return

    # 기본: 인덱스 출력
    if args.json:
        print(json.dumps(index, ensure_ascii=False, indent=2))
    else:
        print(f"\n=== 법령 → YAML 파일 역 인덱스 ===\n")
        print(f"총 {len(index)}개 법령\n")

        for law_name, data in sorted(index.items()):
            file_count = len(data["files"])
            print(f"📚 {law_name} ({file_count}개 파일)")
            for file_info in data["files"]:
                path = file_info["path"]
                items = file_info["items"]
                item_str = f" [{', '.join(items[:3])}{'...' if len(items) > 3 else ''}]" if items else ""
                print(f"   └─ {path}{item_str}")
            print()


if __name__ == "__main__":
    main()
