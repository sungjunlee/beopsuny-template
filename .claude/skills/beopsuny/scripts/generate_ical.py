#!/usr/bin/env python3
"""
iCal Generator for Compliance Calendar

법정 의무 캘린더를 iCal(.ics) 형식으로 변환하여
Google Calendar, Outlook 등에서 구독할 수 있게 합니다.

Usage:
    python generate_ical.py  # 기본: 프로젝트 루트/assets/compliance.ics
    python generate_ical.py --output /path/to/compliance.ics --year 2026

iCal 구독 방법:
    1. 생성된 .ics 파일을 GitHub에 커밋
    2. raw URL 복사: https://raw.githubusercontent.com/.../main/assets/compliance.ics
    3. Google Calendar: 설정 → 다른 캘린더 추가 → URL로 추가
    4. Outlook: 캘린더 추가 → 인터넷에서 구독
"""

import argparse
import calendar
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Any
from uuid import uuid4

import yaml

# 경로 상수
from common.paths import CALENDAR_PATH, ASSETS_DIR, SKILL_DIR


def load_calendar() -> Dict[str, Any]:
    """법정 의무 캘린더 YAML 로드"""
    if not CALENDAR_PATH.exists():
        print(f"ERROR: 캘린더 파일을 찾을 수 없습니다: {CALENDAR_PATH}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(CALENDAR_PATH, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"ERROR: YAML 파싱 오류: {CALENDAR_PATH}", file=sys.stderr)
        print(f"  상세: {e}", file=sys.stderr)
        sys.exit(1)
    except (PermissionError, OSError) as e:
        print(f"ERROR: 파일 읽기 실패: {e}", file=sys.stderr)
        sys.exit(1)

    if data is None:
        print(f"ERROR: 캘린더 파일이 비어 있습니다: {CALENDAR_PATH}", file=sys.stderr)
        sys.exit(1)

    return data


def format_datetime(dt: datetime, all_day: bool = True) -> str:
    """날짜를 iCal 형식으로 변환

    Args:
        dt: datetime 객체
        all_day: True면 DATE, False면 DATETIME

    Returns:
        iCal 형식 문자열
    """
    if all_day:
        return dt.strftime('%Y%m%d')
    return dt.strftime('%Y%m%dT%H%M%SZ')


def escape_text(text: str) -> str:
    """iCal 텍스트 이스케이프"""
    if not text:
        return ""
    # iCal 특수문자 이스케이프
    text = text.replace('\\', '\\\\')
    text = text.replace(',', '\\,')
    text = text.replace(';', '\\;')
    text = text.replace('\n', '\\n')
    return text


def generate_uid(item_id: str, year: int) -> str:
    """고유 UID 생성"""
    return f"{item_id}-{year}@beopsuny.legal-stack"


def create_vevent(
    uid: str,
    summary: str,
    dtstart: datetime,
    description: str = "",
    location: str = "",
    categories: List[str] = None,
    alarm_days: List[int] = None,
    all_day: bool = True,
    priority: str = "medium"
) -> str:
    """VEVENT 블록 생성

    Args:
        uid: 고유 식별자
        summary: 이벤트 제목
        dtstart: 시작 날짜
        description: 설명
        location: 위치 (관할 기관 등)
        categories: 카테고리 목록
        alarm_days: 알람 설정 (며칠 전)
        all_day: 종일 이벤트 여부
        priority: 우선순위 (critical, high, medium, low)

    Returns:
        VEVENT 문자열
    """
    lines = []
    lines.append("BEGIN:VEVENT")
    lines.append(f"UID:{uid}")
    lines.append(f"DTSTAMP:{format_datetime(datetime.now(timezone.utc), all_day=False)}")

    if all_day:
        lines.append(f"DTSTART;VALUE=DATE:{format_datetime(dtstart)}")
        # 종일 이벤트는 DTEND가 다음날
        dtend = dtstart + timedelta(days=1)
        lines.append(f"DTEND;VALUE=DATE:{format_datetime(dtend)}")
    else:
        lines.append(f"DTSTART:{format_datetime(dtstart, all_day=False)}")
        dtend = dtstart + timedelta(hours=1)
        lines.append(f"DTEND:{format_datetime(dtend, all_day=False)}")

    lines.append(f"SUMMARY:{escape_text(summary)}")

    if description:
        lines.append(f"DESCRIPTION:{escape_text(description)}")

    if location:
        lines.append(f"LOCATION:{escape_text(location)}")

    if categories:
        lines.append(f"CATEGORIES:{','.join(categories)}")

    # 우선순위 (1=높음, 5=보통, 9=낮음)
    priority_map = {'critical': 1, 'high': 3, 'medium': 5, 'low': 9}
    lines.append(f"PRIORITY:{priority_map.get(priority, 5)}")

    # 알람 추가
    if alarm_days:
        for days in alarm_days:
            lines.append("BEGIN:VALARM")
            lines.append("ACTION:DISPLAY")
            lines.append(f"TRIGGER:-P{days}D")
            lines.append(f"DESCRIPTION:{escape_text(summary)} - {days}일 전 알림")
            lines.append("END:VALARM")

    lines.append("END:VEVENT")
    return "\n".join(lines)


def generate_ical(year: int = None, include_monthly: bool = True) -> str:
    """iCal 파일 생성

    Args:
        year: 대상 연도 (기본: 올해와 내년)
        include_monthly: 월별 반복 의무 포함 여부

    Returns:
        iCal 형식 문자열
    """
    data = load_calendar()

    if year is None:
        year = datetime.now().year

    events = []

    # VCALENDAR 헤더
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Beopsuny//Compliance Calendar//KO",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_text(data.get('name', '법정 의무 캘린더'))}",
        "X-WR-TIMEZONE:Asia/Seoul",
    ]

    # 연간 의무
    for item in data.get('annual', []):
        deadline_month = item.get('deadline_month')
        deadline_day = item.get('deadline_day', 1)

        if not item.get('name'):
            print(f"WARNING: 'name' 누락으로 건너뜀: {item.get('id', 'unknown')}", file=sys.stderr)
            continue

        if deadline_month:
            # 올해와 내년 두 해 생성
            for y in [year, year + 1]:
                try:
                    deadline = datetime(y, deadline_month, deadline_day)
                except ValueError as e:
                    print(f"WARNING: 날짜 오류로 '{item.get('name')}' 건너뜀 ({y}/{deadline_month}/{deadline_day}): {e}",
                          file=sys.stderr)
                    continue

                description = []
                if item.get('description'):
                    description.append(item['description'])
                if item.get('law'):
                    description.append(f"법적 근거: {item['law']}")
                if item.get('penalty'):
                    description.append(f"벌칙: {item['penalty']}")
                if item.get('notes'):
                    description.append(f"\n{item['notes']}")

                event = create_vevent(
                    uid=generate_uid(item.get('id', str(uuid4())), y),
                    summary=f"⚖️ {item.get('name')}",
                    dtstart=deadline,
                    description="\n".join(description),
                    categories=['법정의무', '연간'],
                    alarm_days=item.get('reminder_days', [30, 7]),
                    priority=item.get('priority', 'medium'),
                )
                events.append(event)

    # 분기 의무 (occurrences 사용)
    for item in data.get('quarterly', []):
        if not item.get('name'):
            print(f"WARNING: 'name' 누락으로 건너뜀: {item.get('id', 'unknown')}", file=sys.stderr)
            continue

        for occ in item.get('occurrences', []):
            occ_month = occ.get('month')
            occ_day = occ.get('day', 1)
            occ_label = occ.get('label', '')

            if occ_month:
                for y in [year, year + 1]:
                    try:
                        deadline = datetime(y, occ_month, occ_day)
                    except ValueError as e:
                        print(f"WARNING: 날짜 오류로 '{item.get('name')}' 건너뜀 ({y}/{occ_month}/{occ_day}): {e}",
                              file=sys.stderr)
                        continue

                    description = []
                    if item.get('description'):
                        description.append(item['description'])
                    if occ_label:
                        description.append(f"분기: {occ_label}")
                    if item.get('law'):
                        description.append(f"법적 근거: {item['law']}")
                    if item.get('penalty'):
                        description.append(f"벌칙: {item['penalty']}")

                    event = create_vevent(
                        uid=generate_uid(f"{item.get('id')}-{occ_month}", y),
                        summary=f"⚖️ {item.get('name')} ({occ_label})" if occ_label else f"⚖️ {item.get('name')}",
                        dtstart=deadline,
                        description="\n".join(description),
                        categories=['법정의무', '분기'],
                        alarm_days=item.get('reminder_days', [14, 7]),
                        priority=item.get('priority', 'medium'),
                    )
                    events.append(event)

    # 월별 의무 (선택적)
    if include_monthly:
        for item in data.get('monthly', []):
            if not item.get('name'):
                print(f"WARNING: 'name' 누락으로 건너뜀: {item.get('id', 'unknown')}", file=sys.stderr)
                continue

            deadline_day = item.get('deadline_day', 10)

            # 12개월분 생성
            for month in range(1, 13):
                for y in [year, year + 1]:
                    # 2월 30일 같은 경우 해당 월의 마지막 날로 조정
                    last_day_of_month = calendar.monthrange(y, month)[1]
                    actual_day = min(deadline_day, last_day_of_month)
                    deadline = datetime(y, month, actual_day)

                    description = []
                    if item.get('description'):
                        description.append(item['description'])
                    if item.get('law'):
                        description.append(f"법적 근거: {item['law']}")

                    event = create_vevent(
                        uid=generate_uid(f"{item.get('id')}-{y}-{month:02d}", y),
                        summary=f"💰 {item.get('name')}",
                        dtstart=deadline,
                        description="\n".join(description),
                        categories=['법정의무', '월별'],
                        alarm_days=item.get('reminder_days', [7, 3]),
                        priority=item.get('priority', 'high'),
                    )
                    events.append(event)

    # 이벤트 추가
    for event in events:
        lines.append(event)

    # VCALENDAR 종료
    lines.append("END:VCALENDAR")

    return "\n".join(lines)


def main():
    # 프로젝트 루트의 assets/ 디렉토리를 기본 출력 위치로 설정
    project_root = SKILL_DIR.parent.parent.parent  # .claude/skills/beopsuny -> 루트
    default_output = project_root / "assets" / "compliance.ics"

    parser = argparse.ArgumentParser(
        description='법정 의무 캘린더 iCal 생성기',
        epilog="""
예시:
  python generate_ical.py  # 기본: 프로젝트 루트/assets/compliance.ics
  python generate_ical.py --output /path/to/output.ics --year 2026 --no-monthly
"""
    )
    parser.add_argument('--output', '-o', default=str(default_output),
                        help=f'출력 파일 경로 (기본: {default_output})')
    parser.add_argument('--year', '-y', type=int, default=None,
                        help='대상 연도 (기본: 올해)')
    parser.add_argument('--no-monthly', action='store_true',
                        help='월별 반복 의무 제외 (파일 크기 감소)')
    parser.add_argument('--stdout', action='store_true',
                        help='파일 대신 stdout으로 출력')

    args = parser.parse_args()

    ical_content = generate_ical(
        year=args.year,
        include_monthly=not args.no_monthly
    )

    if args.stdout:
        print(ical_content)
    else:
        output_path = Path(args.output)

        # 부모 디렉토리가 없으면 생성
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            print(f"ERROR: 디렉토리 생성 권한이 없습니다: {output_path.parent}", file=sys.stderr)
            sys.exit(1)
        except OSError as e:
            print(f"ERROR: 디렉토리 생성 실패: {e}", file=sys.stderr)
            sys.exit(1)

        # 파일 쓰기
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(ical_content)
        except PermissionError:
            print(f"ERROR: 파일 쓰기 권한이 없습니다: {output_path}", file=sys.stderr)
            print("  다른 경로를 지정하거나 권한을 확인하세요.", file=sys.stderr)
            sys.exit(1)
        except OSError as e:
            print(f"ERROR: 파일 쓰기 실패: {e}", file=sys.stderr)
            sys.exit(1)

        print(f"✅ iCal 파일 생성됨: {output_path}")
        print(f"   이벤트 수: {ical_content.count('BEGIN:VEVENT')}개")
        print()
        print("📅 캘린더 구독 방법:")
        print("   1. 이 파일을 GitHub에 커밋")
        print("   2. raw URL 복사")
        print("   3. Google Calendar: 설정 → 다른 캘린더 추가 → URL로 추가")


if __name__ == '__main__':
    main()
