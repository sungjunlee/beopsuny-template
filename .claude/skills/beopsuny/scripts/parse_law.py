#!/usr/bin/env python3
"""
Korean Law Parser - XML to Markdown 변환기

Usage:
    python parse_law.py data/raw/민법_123456.xml
    python parse_law.py data/raw/민법_123456.xml --output data/parsed/민법.md
    python parse_law.py data/raw/민법_123456.xml --article 750  # 특정 조문만
"""

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
DATA_PARSED_DIR = SKILL_DIR / "data" / "parsed"


def parse_law_xml(xml_path: Path) -> dict:
    """XML 파일을 파싱하여 구조화된 딕셔너리로 반환"""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    law_data = {
        'basic_info': {},
        'articles': [],
        'addenda': [],
        'tables': [],
    }

    # 기본 정보 추출
    basic_info = law_data['basic_info']
    basic_info['law_id'] = root.findtext('.//법령ID', '')
    basic_info['name'] = root.findtext('.//법령명_한글', '') or root.findtext('.//법령명', '')
    basic_info['name_hanja'] = root.findtext('.//법령명_한자', '')
    basic_info['promul_date'] = root.findtext('.//공포일자', '')
    basic_info['promul_no'] = root.findtext('.//공포번호', '')
    basic_info['enforce_date'] = root.findtext('.//시행일자', '')
    basic_info['ministry'] = root.findtext('.//소관부처명', '')
    basic_info['law_type'] = root.findtext('.//법종구분', '')
    basic_info['revision_type'] = root.findtext('.//제개정구분명', '')

    # 조문 추출
    for article_unit in root.findall('.//조문단위'):
        article = {
            'number': article_unit.findtext('조문번호', ''),
            'branch_number': article_unit.findtext('조문가지번호', ''),
            'title': article_unit.findtext('조문제목', ''),
            'content': article_unit.findtext('조문내용', ''),
            'enforce_date': article_unit.findtext('조문시행일자', ''),
            'paragraphs': [],
        }

        # 항 추출
        for para in article_unit.findall('.//항'):
            paragraph = {
                'number': para.findtext('항번호', ''),
                'content': para.findtext('항내용', ''),
                'items': [],
            }

            # 호 추출
            for item in para.findall('.//호'):
                subitem = {
                    'number': item.findtext('호번호', ''),
                    'content': item.findtext('호내용', ''),
                    'subitems': [],
                }

                # 목 추출
                for subsubitem in item.findall('.//목'):
                    subitem['subitems'].append({
                        'number': subsubitem.findtext('목번호', ''),
                        'content': subsubitem.findtext('목내용', ''),
                    })

                paragraph['items'].append(subitem)

            article['paragraphs'].append(paragraph)

        law_data['articles'].append(article)

    # 부칙 추출
    for addendum_unit in root.findall('.//부칙단위'):
        addendum = {
            'promul_date': addendum_unit.findtext('부칙공포일자', ''),
            'promul_no': addendum_unit.findtext('부칙공포번호', ''),
            'content': addendum_unit.findtext('부칙내용', ''),
        }
        law_data['addenda'].append(addendum)

    return law_data


def format_article_number(number: str, branch: str = '') -> str:
    """조문 번호 포맷팅 (제1조, 제1조의2 등)"""
    if branch:
        return f"제{number}조의{branch}"
    return f"제{number}조"


def convert_paragraph_marker(number: str) -> str:
    """항 번호를 원문자로 변환 또는 그대로 반환"""
    # 이미 원문자인 경우 그대로 반환
    circled_numbers = '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳'
    if number and number[0] in circled_numbers:
        return number

    # 숫자인 경우 원문자로 변환
    markers = ['', '①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩',
               '⑪', '⑫', '⑬', '⑭', '⑮', '⑯', '⑰', '⑱', '⑲', '⑳']
    try:
        idx = int(number)
        if 0 < idx < len(markers):
            return markers[idx]
    except (ValueError, TypeError):
        pass
    return f"({number})"


def clean_item_number(number: str) -> str:
    """호 번호 정리 (1. → 1)"""
    return number.rstrip('.')


def generate_frontmatter(info: dict, article_filter: str = None) -> str:
    """YAML frontmatter 생성"""
    import urllib.parse
    from datetime import datetime

    law_name = info['name']
    law_id = info['law_id']

    # 출처 URL 생성
    source_url = f"https://www.law.go.kr/법령/{urllib.parse.quote(law_name)}"
    if article_filter:
        source_url += f"/제{article_filter}조"

    lines = [
        "---",
        f"title: \"{law_name}\"",
        f"law_id: \"{law_id}\"",
        f"type: 법령",
        f"law_type: \"{info.get('law_type', '')}\"",
        f"ministry: \"{info.get('ministry', '')}\"",
        f"promulgation_date: \"{info.get('promul_date', '')}\"",
        f"enforcement_date: \"{info.get('enforce_date', '')}\"",
        f"revision_type: \"{info.get('revision_type', '')}\"",
        f"source_url: \"{source_url}\"",
        f"source_name: \"국가법령정보센터\"",
        f"retrieved_at: \"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\"",
    ]

    if article_filter:
        lines.append(f"article_filter: \"{article_filter}\"")

    # 관련 태그
    tags = ["법령", info.get('law_type', ''), info.get('ministry', '')]
    tags = [t for t in tags if t]  # 빈 값 제거
    lines.append(f"tags: {tags}")

    lines.append("---")
    lines.append("")

    return '\n'.join(lines)


def to_markdown(law_data: dict, article_filter: str = None) -> str:
    """구조화된 데이터를 Markdown으로 변환"""
    lines = []
    info = law_data['basic_info']

    # Frontmatter 추가
    lines.append(generate_frontmatter(info, article_filter))

    # 제목
    lines.append(f"# {info['name']}")
    if info['name_hanja']:
        lines.append(f"*{info['name_hanja']}*")
    lines.append("")

    # 기본 정보 테이블
    lines.append("## 기본 정보")
    lines.append("")
    lines.append("| 항목 | 내용 |")
    lines.append("|------|------|")
    lines.append(f"| 법령ID | {info['law_id']} |")
    lines.append(f"| 법종구분 | {info['law_type']} |")
    lines.append(f"| 소관부처 | {info['ministry']} |")
    lines.append(f"| 공포일자 | {info['promul_date']} |")
    lines.append(f"| 공포번호 | {info['promul_no']} |")
    lines.append(f"| 시행일자 | {info['enforce_date']} |")
    lines.append(f"| 제개정구분 | {info['revision_type']} |")
    lines.append("")

    # 조문
    lines.append("## 조문")
    lines.append("")

    for article in law_data['articles']:
        article_num = format_article_number(article['number'], article['branch_number'])

        # 특정 조문 필터링
        if article_filter:
            if article['number'] != article_filter and article_num != f"제{article_filter}조":
                continue

        # 조문 제목이 없고 내용에 "장" 또는 "절"만 있는 경우 스킵 (구조 구분용)
        content_stripped = (article['content'] or '').strip()
        if not article['title'] and content_stripped:
            # 장/절/관 구분인지 확인 (예: "제5장 불법행위")
            if re.match(r'^[\s\n]*제\d+[장절관편]', content_stripped):
                continue

        # 조문 제목
        title = f"### {article_num}"
        if article['title']:
            title += f" ({article['title']})"
        lines.append(title)
        lines.append("")

        # 조문 내용 - 조문번호와 제목 중복 제거
        if article['content']:
            content = article['content'].strip()
            # "제750조(불법행위의 내용)" 같은 중복 제거
            content = re.sub(r'^제\d+조(?:의\d+)?(?:\([^)]+\))?\s*', '', content)
            if content:
                lines.append(f"> {content}")
                lines.append("")

        # 항
        for para in article['paragraphs']:
            para_marker = convert_paragraph_marker(para['number'])
            if para['content']:
                # 항 내용에서 중복된 항 번호 제거 (예: "① 개인정보처리자는..." → "개인정보처리자는...")
                content = re.sub(r'^[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]\s*', '', para['content'].strip())
                lines.append(f"{para_marker} {content}")

            # 호
            for item in para['items']:
                if item['content']:
                    # 호 내용에서 중복된 호 번호 제거 (예: "1. 정보주체의..." → "정보주체의...")
                    content = re.sub(r'^\d+\.\s*', '', item['content'].strip())
                    item_num = clean_item_number(item['number'])
                    lines.append(f"   {item_num}. {content}")

                # 목
                for subitem in item['subitems']:
                    if subitem['content']:
                        content = re.sub(r'^[가-힣]\.\s*', '', subitem['content'].strip())
                        lines.append(f"      {subitem['number']}. {content}")

            lines.append("")

        # 조문 시행일
        if article['enforce_date']:
            lines.append(f"*시행일: {article['enforce_date']}*")
            lines.append("")

        lines.append("---")
        lines.append("")

    # 부칙
    if law_data['addenda'] and not article_filter:
        lines.append("## 부칙")
        lines.append("")

        for addendum in law_data['addenda']:
            lines.append(f"### 부칙 (공포 {addendum['promul_date']}, 제{addendum['promul_no']}호)")
            lines.append("")
            if addendum['content']:
                # 부칙 내용 정리 (HTML 태그 제거)
                content = re.sub(r'<[^>]+>', '', addendum['content'])
                lines.append(content)
            lines.append("")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Korean Law XML to Markdown Parser')
    parser.add_argument('xml_file', help='XML 파일 경로')
    parser.add_argument('--output', '-o', help='출력 파일 경로')
    parser.add_argument('--article', '-a', help='특정 조문만 추출 (예: 750)')
    parser.add_argument('--print', '-p', action='store_true', help='표준출력으로 출력')

    args = parser.parse_args()

    xml_path = Path(args.xml_file)
    if not xml_path.exists():
        print(f"Error: File not found - {xml_path}", file=sys.stderr)
        sys.exit(1)

    # 파싱
    law_data = parse_law_xml(xml_path)

    # Markdown 변환
    markdown = to_markdown(law_data, args.article)

    # 출력
    if args.print or not args.output:
        print(markdown)
    else:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown)
        print(f"저장됨: {output_path}")

    # 기본 출력 경로로도 저장
    if not args.print and not args.output:
        safe_name = "".join(c for c in law_data['basic_info']['name']
                           if c.isalnum() or c in (' ', '_', '-')).strip()
        output_path = DATA_PARSED_DIR / f"{safe_name}.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown)
        print(f"\n저장됨: {output_path}")


if __name__ == '__main__':
    main()
