#!/usr/bin/env python3
"""
Korean Law Link Generator - 법령/판례 링크 생성기

Usage:
    python gen_link.py law "민법" --article 750
    python gen_link.py law "개인정보보호법" --article 15 --paragraph 1
    python gen_link.py case "2022다12345"
    python gen_link.py search "개인정보보호법"
    python gen_link.py decree "개인정보보호법"
"""

import argparse
import urllib.parse
import sys


def generate_law_link(law_name: str, article: str = None, paragraph: str = None) -> dict:
    """
    법령 링크 생성

    Args:
        law_name: 법령명
        article: 조문 번호 (선택)
        paragraph: 항 번호 (선택)

    Returns:
        dict with various link formats
    """
    encoded_name = urllib.parse.quote(law_name)

    links = {
        'law_go_kr': f"https://www.law.go.kr/법령/{encoded_name}",
        'law_name': law_name,
    }

    if article:
        article_str = f"제{article}조"
        if paragraph:
            article_str += f"제{paragraph}항"
        links['law_go_kr_article'] = f"https://www.law.go.kr/법령/{encoded_name}/{article_str}"
        links['article'] = article_str

    return links


def generate_case_link(case_number: str) -> dict:
    """
    판례 링크 생성

    Args:
        case_number: 사건번호 (예: 2022다12345)

    Returns:
        dict with various link formats
    """
    # 공백 제거
    clean_number = case_number.replace(' ', '')

    links = {
        'case_number': case_number,
        'law_go_kr': f"https://www.law.go.kr/판례/({clean_number})",
        'scourt': "https://glaw.scourt.go.kr/wsjo/intesrch/sjo022.do",
        'casenote': f"https://casenote.kr/search?query={urllib.parse.quote(case_number)}",
        'bigcase': f"https://bigcase.ai/search?q={urllib.parse.quote(case_number)}",
    }

    return links


def generate_search_link(query: str, target: str = "law") -> dict:
    """
    검색 링크 생성

    Args:
        query: 검색어
        target: 검색 대상 (law, prec, ordin)

    Returns:
        dict with search links
    """
    encoded_query = urllib.parse.quote(query)

    target_paths = {
        'law': '법령',
        'prec': '판례',
        'ordin': '자치법규',
    }
    path = target_paths.get(target, '법령')

    links = {
        'query': query,
        'law_go_kr': f"https://www.law.go.kr/{path}/{encoded_query}",
    }

    if target == 'prec':
        links['scourt'] = f"https://glaw.scourt.go.kr/wsjo/intesrch/sjo022.do?query={encoded_query}"
        links['casenote'] = f"https://casenote.kr/search?query={encoded_query}"
        links['bigcase'] = f"https://bigcase.ai/search?q={encoded_query}"

    return links


def generate_decree_links(law_name: str) -> dict:
    """
    시행령/시행규칙 링크 생성

    Args:
        law_name: 법률명 (예: 개인정보보호법)

    Returns:
        dict with decree and rule links
    """
    links = {
        'law_name': law_name,
        'law': f"https://www.law.go.kr/법령/{urllib.parse.quote(law_name)}",
        'decree': f"https://www.law.go.kr/법령/{urllib.parse.quote(law_name + ' 시행령')}",
        'rule': f"https://www.law.go.kr/법령/{urllib.parse.quote(law_name + ' 시행규칙')}",
    }

    return links


def generate_history_link(law_name: str, law_id: str = None) -> dict:
    """
    연혁법령 링크 생성

    Args:
        law_name: 법령명
        law_id: 법령ID (선택, 있으면 더 정확한 링크 생성)

    Returns:
        dict with history links
    """
    encoded_name = urllib.parse.quote(law_name)

    links = {
        'law_name': law_name,
        'current': f"https://www.law.go.kr/법령/{encoded_name}",
        'history_list': f"https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=0&efYd=0&lsId={law_id or ''}&ancYnChk=0&ancYd=&nwJoYnInfo=N&efGubun=Y&chrClsCd=010202&urlMode=lsHstInfoR&viewCls=lsHstInfoR&lsNm={encoded_name}",
        'revision_compare': f"https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=0&lsId={law_id or ''}&efYd=0&chrClsCd=010202&urlMode=lsSc&viewCls=lsSc&lsNm={encoded_name}",
        'note': "연혁법령 API는 공개되지 않아 웹 링크로 제공합니다. 직접 방문하여 확인하세요."
    }

    if law_id:
        links['law_id'] = law_id

    return links


def print_links(links: dict, format_type: str = "markdown"):
    """링크 출력"""
    if format_type == "markdown":
        print("\n### 생성된 링크\n")
        for key, value in links.items():
            if value.startswith('http'):
                print(f"- **{key}**: [{value}]({value})")
            else:
                print(f"- **{key}**: {value}")
    else:
        for key, value in links.items():
            print(f"{key}: {value}")


def main():
    parser = argparse.ArgumentParser(description='Korean Law Link Generator')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # law 명령
    law_parser = subparsers.add_parser('law', help='법령 링크 생성')
    law_parser.add_argument('name', help='법령명')
    law_parser.add_argument('--article', '-a', help='조문 번호')
    law_parser.add_argument('--paragraph', '-p', help='항 번호')
    law_parser.add_argument('--format', '-f', default='markdown', choices=['markdown', 'plain'])

    # case 명령
    case_parser = subparsers.add_parser('case', help='판례 링크 생성')
    case_parser.add_argument('number', help='사건번호 (예: 2022다12345)')
    case_parser.add_argument('--format', '-f', default='markdown', choices=['markdown', 'plain'])

    # search 명령
    search_parser = subparsers.add_parser('search', help='검색 링크 생성')
    search_parser.add_argument('query', help='검색어')
    search_parser.add_argument('--type', '-t', default='law', choices=['law', 'prec', 'ordin'])
    search_parser.add_argument('--format', '-f', default='markdown', choices=['markdown', 'plain'])

    # decree 명령
    decree_parser = subparsers.add_parser('decree', help='시행령/시행규칙 링크 생성')
    decree_parser.add_argument('name', help='법률명')
    decree_parser.add_argument('--format', '-f', default='markdown', choices=['markdown', 'plain'])

    # history 명령
    history_parser = subparsers.add_parser('history', help='연혁법령 링크 생성')
    history_parser.add_argument('name', help='법령명')
    history_parser.add_argument('--id', help='법령ID (선택)')
    history_parser.add_argument('--format', '-f', default='markdown', choices=['markdown', 'plain'])

    args = parser.parse_args()

    if args.command == 'law':
        links = generate_law_link(args.name, args.article, args.paragraph)
        print_links(links, args.format)
    elif args.command == 'case':
        links = generate_case_link(args.number)
        print_links(links, args.format)
    elif args.command == 'search':
        links = generate_search_link(args.query, args.type)
        print_links(links, args.format)
    elif args.command == 'decree':
        links = generate_decree_links(args.name)
        print_links(links, args.format)
    elif args.command == 'history':
        links = generate_history_link(args.name, args.id)
        print_links(links, args.format)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
