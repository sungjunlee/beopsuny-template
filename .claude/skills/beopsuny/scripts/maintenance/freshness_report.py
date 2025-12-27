#!/usr/bin/env python3
"""
데이터 신선도 리포트

각 YAML 파일의 last_updated와 next_review 필드를 확인하여
리뷰가 필요한 파일을 식별합니다.

Usage:
    python freshness_report.py              # 리포트 출력
    python freshness_report.py --overdue    # 기한 지난 파일만
    python freshness_report.py --markdown   # GitHub Issue용 마크다운
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import yaml

# 경로 설정
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent.parent
ASSETS_DIR = SKILL_DIR / "assets"
CHECKLISTS_DIR = ASSETS_DIR / "checklists"


def parse_date(date_str: str) -> datetime:
    """날짜 문자열 파싱 (YYYY-MM-DD 또는 YYYY-MM)"""
    if not date_str:
        return None

    date_str = str(date_str).strip()

    # YYYY-MM 형식
    if len(date_str) == 7:
        return datetime.strptime(date_str, "%Y-%m")

    # YYYY-MM-DD 형식
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None


def get_file_metadata(filepath: Path) -> dict:
    """YAML 파일에서 메타데이터 추출"""
    with open(filepath, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    maintenance = data.get("maintenance", {})

    return {
        "path": str(filepath.relative_to(ASSETS_DIR)),
        "name": data.get("name", filepath.stem),
        "type": data.get("type", "unknown"),
        "last_updated": data.get("last_updated"),
        "review_cycle": maintenance.get("review_cycle"),
        "next_review": maintenance.get("next_review"),
        "volatile_items": maintenance.get("volatile_items", []),
        "note": maintenance.get("note"),
    }


def collect_all_metadata() -> list:
    """모든 YAML 파일의 메타데이터 수집"""
    yaml_files = [
        ASSETS_DIR / "compliance_calendar.yaml",
        ASSETS_DIR / "clause_references.yaml",
        ASSETS_DIR / "legal_terms.yaml",
        ASSETS_DIR / "forms.yaml",
    ]
    yaml_files.extend(CHECKLISTS_DIR.glob("*.yaml"))

    metadata = []
    for filepath in yaml_files:
        if filepath.exists():
            try:
                meta = get_file_metadata(filepath)
                metadata.append(meta)
            except (yaml.YAMLError, OSError, UnicodeDecodeError) as e:
                print(f"Warning: {filepath} 파싱 실패: {e}", file=sys.stderr)

    return metadata


def analyze_freshness(metadata: list) -> dict:
    """신선도 분석"""
    today = datetime.now()

    overdue = []
    upcoming = []
    fresh = []
    no_review = []

    for meta in metadata:
        next_review = parse_date(meta.get("next_review"))

        if next_review is None:
            no_review.append(meta)
        elif next_review < today:
            days_overdue = (today - next_review).days
            meta["days_overdue"] = days_overdue
            overdue.append(meta)
        elif (next_review - today).days <= 30:
            days_until = (next_review - today).days
            meta["days_until"] = days_until
            upcoming.append(meta)
        else:
            meta["days_until"] = (next_review - today).days
            fresh.append(meta)

    # 정렬
    overdue.sort(key=lambda x: x.get("days_overdue", 0), reverse=True)
    upcoming.sort(key=lambda x: x.get("days_until", 0))

    return {
        "overdue": overdue,
        "upcoming": upcoming,
        "fresh": fresh,
        "no_review": no_review,
    }


def format_markdown(analysis: dict) -> str:
    """GitHub Issue용 마크다운 생성"""
    overdue = analysis["overdue"]
    upcoming = analysis["upcoming"]
    no_review = analysis["no_review"]

    lines = [
        "## 📅 데이터 신선도 리포트",
        "",
        f"- 🚨 리뷰 기한 초과: {len(overdue)}개",
        f"- ⚠️ 30일 내 리뷰 필요: {len(upcoming)}개",
        f"- ✅ 신선: {len(analysis['fresh'])}개",
        f"- ❓ 리뷰 주기 미설정: {len(no_review)}개",
        "",
    ]

    if overdue:
        lines.append("### 🚨 리뷰 기한 초과")
        lines.append("")
        for meta in overdue:
            days = meta.get("days_overdue", 0)
            lines.append(f"- [ ] **{meta['path']}** ({days}일 초과)")
            lines.append(f"  - 마지막 업데이트: {meta.get('last_updated', 'N/A')}")
            lines.append(f"  - 리뷰 예정일: {meta.get('next_review', 'N/A')}")
            if meta.get("volatile_items"):
                lines.append(f"  - 변동 항목: {', '.join(meta['volatile_items'][:3])}")
        lines.append("")

    if upcoming:
        lines.append("### ⚠️ 30일 내 리뷰 필요")
        lines.append("")
        for meta in upcoming:
            days = meta.get("days_until", 0)
            lines.append(f"- [ ] **{meta['path']}** ({days}일 후)")
        lines.append("")

    if no_review:
        lines.append("### ❓ 리뷰 주기 미설정")
        lines.append("")
        for meta in no_review:
            lines.append(f"- {meta['path']}")
        lines.append("")

    lines.extend([
        "### 권장 조치",
        "",
        "1. 기한 초과 파일부터 리뷰",
        "2. 법령 개정 여부 확인 ([법령정보센터](https://www.law.go.kr))",
        "3. `last_updated`, `next_review` 필드 갱신",
        "",
        "---",
        f"*생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
    ])

    return "\n".join(lines)


def format_text(analysis: dict) -> str:
    """터미널 출력용 텍스트"""
    overdue = analysis["overdue"]
    upcoming = analysis["upcoming"]

    lines = [
        "",
        "=== 데이터 신선도 리포트 ===",
        "",
        f"🚨 리뷰 기한 초과: {len(overdue)}개",
        f"⚠️  30일 내 리뷰 필요: {len(upcoming)}개",
        f"✅ 신선: {len(analysis['fresh'])}개",
        f"❓ 리뷰 주기 미설정: {len(analysis['no_review'])}개",
        "",
    ]

    if overdue:
        lines.append("🚨 리뷰 기한 초과:")
        for meta in overdue:
            days = meta.get("days_overdue", 0)
            lines.append(f"   {meta['path']} ({days}일 초과)")
            lines.append(f"      last_updated: {meta.get('last_updated', 'N/A')}")
            lines.append(f"      next_review: {meta.get('next_review', 'N/A')}")
        lines.append("")

    if upcoming:
        lines.append("⚠️  30일 내 리뷰 필요:")
        for meta in upcoming:
            days = meta.get("days_until", 0)
            lines.append(f"   {meta['path']} ({days}일 후)")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="데이터 신선도 리포트")
    parser.add_argument("--overdue", action="store_true", help="기한 초과 파일만 출력")
    parser.add_argument("--markdown", action="store_true", help="마크다운 출력")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    args = parser.parse_args()

    # 메타데이터 수집
    metadata = collect_all_metadata()
    print(f"총 {len(metadata)}개 파일 확인", file=sys.stderr)

    # 분석
    analysis = analyze_freshness(metadata)

    # 출력
    if args.json:
        print(json.dumps(analysis, ensure_ascii=False, indent=2, default=str))
    elif args.markdown:
        print(format_markdown(analysis))
    elif args.overdue:
        if analysis["overdue"]:
            for meta in analysis["overdue"]:
                print(f"{meta['path']} ({meta.get('days_overdue', 0)}일 초과)")
        else:
            print("기한 초과 파일 없음")
    else:
        print(format_text(analysis))

    # 종료 코드: 기한 초과 파일이 있으면 1
    sys.exit(1 if analysis["overdue"] else 0)


if __name__ == "__main__":
    main()
