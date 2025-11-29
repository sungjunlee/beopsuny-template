#!/usr/bin/env python3
"""
Korean Law Comparator - 법령 개정 전후 비교

Usage:
    python compare_law.py "민법" --before 20240101 --after 20250101
    python compare_law.py data/raw/old.xml data/raw/new.xml
"""

import argparse
import difflib
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent


def extract_articles_from_xml(xml_path: Path) -> dict:
    """XML에서 조문 딕셔너리 추출"""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    articles = {}

    for article_unit in root.findall('.//조문단위'):
        number = article_unit.findtext('조문번호', '')
        branch = article_unit.findtext('조문가지번호', '')
        title = article_unit.findtext('조문제목', '')
        content = article_unit.findtext('조문내용', '')

        # 항 내용 추가
        full_content = [content] if content else []

        for para in article_unit.findall('.//항'):
            para_num = para.findtext('항번호', '')
            para_content = para.findtext('항내용', '')
            if para_content:
                full_content.append(f"({para_num}) {para_content}")

            for item in para.findall('.//호'):
                item_num = item.findtext('호번호', '')
                item_content = item.findtext('호내용', '')
                if item_content:
                    full_content.append(f"  {item_num}. {item_content}")

        key = f"{number}" if not branch else f"{number}의{branch}"
        articles[key] = {
            'number': number,
            'branch': branch,
            'title': title,
            'content': '\n'.join(full_content),
        }

    return articles


def compare_articles(old_articles: dict, new_articles: dict) -> dict:
    """두 버전의 조문 비교"""
    changes = {
        'added': [],
        'removed': [],
        'modified': [],
        'unchanged': [],
    }

    old_keys = set(old_articles.keys())
    new_keys = set(new_articles.keys())

    # 추가된 조문
    for key in new_keys - old_keys:
        changes['added'].append({
            'article': key,
            'title': new_articles[key]['title'],
            'content': new_articles[key]['content'],
        })

    # 삭제된 조문
    for key in old_keys - new_keys:
        changes['removed'].append({
            'article': key,
            'title': old_articles[key]['title'],
            'content': old_articles[key]['content'],
        })

    # 수정된 조문
    for key in old_keys & new_keys:
        old_content = old_articles[key]['content']
        new_content = new_articles[key]['content']

        if old_content != new_content:
            # diff 생성
            diff = list(difflib.unified_diff(
                old_content.splitlines(),
                new_content.splitlines(),
                lineterm='',
                fromfile='이전',
                tofile='현행',
            ))

            changes['modified'].append({
                'article': key,
                'old_title': old_articles[key]['title'],
                'new_title': new_articles[key]['title'],
                'diff': '\n'.join(diff),
                'old_content': old_content,
                'new_content': new_content,
            })
        else:
            changes['unchanged'].append(key)

    return changes


def format_comparison_report(changes: dict, law_name: str = "") -> str:
    """비교 결과를 Markdown 보고서로 포맷팅"""
    lines = []

    lines.append(f"# {law_name} 개정 비교 보고서")
    lines.append("")
    lines.append("## 요약")
    lines.append("")
    lines.append(f"- 추가된 조문: {len(changes['added'])}건")
    lines.append(f"- 삭제된 조문: {len(changes['removed'])}건")
    lines.append(f"- 수정된 조문: {len(changes['modified'])}건")
    lines.append(f"- 변경 없음: {len(changes['unchanged'])}건")
    lines.append("")

    # 추가된 조문
    if changes['added']:
        lines.append("## 🆕 추가된 조문")
        lines.append("")
        for item in changes['added']:
            lines.append(f"### 제{item['article']}조")
            if item['title']:
                lines.append(f"**{item['title']}**")
            lines.append("")
            lines.append("```")
            lines.append(item['content'])
            lines.append("```")
            lines.append("")

    # 삭제된 조문
    if changes['removed']:
        lines.append("## ❌ 삭제된 조문")
        lines.append("")
        for item in changes['removed']:
            lines.append(f"### 제{item['article']}조")
            if item['title']:
                lines.append(f"**{item['title']}**")
            lines.append("")
            lines.append("```")
            lines.append(item['content'])
            lines.append("```")
            lines.append("")

    # 수정된 조문
    if changes['modified']:
        lines.append("## 📝 수정된 조문")
        lines.append("")
        for item in changes['modified']:
            lines.append(f"### 제{item['article']}조")
            title = item['new_title'] or item['old_title']
            if title:
                lines.append(f"**{title}**")
            lines.append("")
            lines.append("**이전:**")
            lines.append("```")
            lines.append(item['old_content'])
            lines.append("```")
            lines.append("")
            lines.append("**현행:**")
            lines.append("```")
            lines.append(item['new_content'])
            lines.append("```")
            lines.append("")
            lines.append("**변경 내용 (diff):**")
            lines.append("```diff")
            lines.append(item['diff'])
            lines.append("```")
            lines.append("")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Korean Law Comparator')
    parser.add_argument('old_file', help='이전 버전 XML 파일')
    parser.add_argument('new_file', help='현행 버전 XML 파일')
    parser.add_argument('--name', '-n', default='법령', help='법령명')
    parser.add_argument('--output', '-o', help='출력 파일 경로')

    args = parser.parse_args()

    old_path = Path(args.old_file)
    new_path = Path(args.new_file)

    if not old_path.exists():
        print(f"Error: File not found - {old_path}", file=sys.stderr)
        sys.exit(1)

    if not new_path.exists():
        print(f"Error: File not found - {new_path}", file=sys.stderr)
        sys.exit(1)

    # 조문 추출
    old_articles = extract_articles_from_xml(old_path)
    new_articles = extract_articles_from_xml(new_path)

    print(f"이전 버전: {len(old_articles)}개 조문")
    print(f"현행 버전: {len(new_articles)}개 조문")

    # 비교
    changes = compare_articles(old_articles, new_articles)

    # 보고서 생성
    report = format_comparison_report(changes, args.name)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n보고서 저장됨: {args.output}")
    else:
        print(report)


if __name__ == '__main__':
    main()
