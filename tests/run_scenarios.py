#!/usr/bin/env python3
"""
법순이 시나리오 테스트 실행기

Usage:
    python tests/run_scenarios.py                    # 모든 시나리오 목록
    python tests/run_scenarios.py --run basic-01     # 특정 시나리오 실행
    python tests/run_scenarios.py --run-category 01  # 카테고리별 실행
    python tests/run_scenarios.py --pilot            # 파일럿 테스트 (3개)
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

# 경로 설정
TESTS_DIR = Path(__file__).parent
SCENARIOS_DIR = TESTS_DIR / "scenarios"
RESULTS_DIR = TESTS_DIR / "results"
PROJECT_ROOT = TESTS_DIR.parent
SCRIPTS_DIR = PROJECT_ROOT / ".claude" / "skills" / "beopsuny" / "scripts"


def load_all_scenarios():
    """모든 시나리오 파일 로드"""
    scenarios = {}
    for yaml_file in sorted(SCENARIOS_DIR.glob("*.yaml")):
        with open(yaml_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            category_name = yaml_file.stem
            scenarios[category_name] = data
    return scenarios


def list_scenarios(scenarios):
    """시나리오 목록 출력"""
    print("\n" + "=" * 60)
    print("법순이 테스트 시나리오 목록")
    print("=" * 60)

    total = 0
    for category_name, data in scenarios.items():
        print(f"\n📁 {data.get('name', category_name)}")
        print(f"   {data.get('description', '').split(chr(10))[0][:50]}...")

        for scenario in data.get("scenarios", []):
            sid = scenario.get("id", "?")
            name = scenario.get("name", "이름 없음")
            persona = scenario.get("persona", "")
            print(f"   • [{sid}] {name}")
            if persona:
                print(f"     👤 {persona}")
            total += 1

    print("\n" + "-" * 60)
    print(f"총 {total}개 시나리오")
    print("=" * 60 + "\n")


def find_scenario(scenarios, scenario_id):
    """ID로 시나리오 찾기"""
    for category_name, data in scenarios.items():
        for scenario in data.get("scenarios", []):
            if scenario.get("id") == scenario_id:
                return category_name, scenario
    return None, None


def run_command(command, cwd=None):
    """명령어 실행 및 결과 반환"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=cwd or PROJECT_ROOT,
            timeout=60,
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": "Timeout (60s)",
            "returncode": -1,
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "returncode": -1,
        }


def run_scenario(category_name, scenario):
    """단일 시나리오 실행"""
    sid = scenario.get("id", "unknown")
    name = scenario.get("name", "이름 없음")
    question = scenario.get("question", "")
    command = scenario.get("command", "")
    command_sequence = scenario.get("command_sequence", [])

    print(f"\n{'─' * 50}")
    print(f"🧪 [{sid}] {name}")
    print(f"{'─' * 50}")
    print(f"📝 질문: {question[:100]}...")

    results = []

    # 단일 명령어 또는 명령어 시퀀스 실행
    commands = command_sequence if command_sequence else [command] if command else []

    for i, cmd in enumerate(commands):
        if not cmd or not cmd.strip():
            continue

        cmd = cmd.strip()
        print(f"\n▶ 실행 [{i+1}/{len(commands)}]: {cmd[:60]}...")

        result = run_command(cmd)
        results.append({
            "command": cmd,
            "result": result,
        })

        if result["success"]:
            output = result["stdout"][:500]
            print(f"✅ 성공")
            if output:
                print(f"   출력 미리보기:\n   {output[:200]}...")
        else:
            print(f"❌ 실패: {result['stderr'][:100]}")

    return {
        "id": sid,
        "name": name,
        "category": category_name,
        "question": question,
        "expected": scenario.get("expected", {}),
        "command_results": results,
        "timestamp": datetime.now().isoformat(),
    }


def run_pilot_test(scenarios):
    """파일럿 테스트 - 핵심 3개 시나리오"""
    pilot_ids = ["basic-01", "admrul-01", "edge-01"]

    print("\n" + "=" * 60)
    print("🚀 파일럿 테스트 실행")
    print("   3개 핵심 시나리오로 기본 동작 검증")
    print("=" * 60)

    results = []
    for sid in pilot_ids:
        category, scenario = find_scenario(scenarios, sid)
        if scenario:
            result = run_scenario(category, scenario)
            results.append(result)
        else:
            print(f"⚠️  시나리오 '{sid}' 를 찾을 수 없습니다.")

    # 결과 저장
    save_results(results, "pilot")
    return results


def run_category(scenarios, category_prefix):
    """카테고리별 시나리오 실행"""
    results = []

    for category_name, data in scenarios.items():
        if category_name.startswith(category_prefix):
            print(f"\n{'=' * 60}")
            print(f"📁 카테고리: {data.get('name', category_name)}")
            print("=" * 60)

            for scenario in data.get("scenarios", []):
                result = run_scenario(category_name, scenario)
                results.append(result)

    if results:
        save_results(results, f"category_{category_prefix}")
    else:
        print(f"⚠️  카테고리 '{category_prefix}'를 찾을 수 없습니다.")

    return results


def save_results(results, prefix="test"):
    """결과 저장"""
    RESULTS_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.json"
    filepath = RESULTS_DIR / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n📄 결과 저장: {filepath}")
    return filepath


def print_summary(results):
    """결과 요약 출력"""
    print("\n" + "=" * 60)
    print("📊 테스트 결과 요약")
    print("=" * 60)

    total = len(results)
    success = sum(1 for r in results if all(
        cr["result"]["success"] for cr in r.get("command_results", [])
    ))

    print(f"   총 시나리오: {total}")
    print(f"   성공: {success}")
    print(f"   실패: {total - success}")

    if total > 0:
        print(f"   성공률: {success/total*100:.1f}%")

    print("\n" + "─" * 60)
    print("다음 단계:")
    print("  1. results/ 디렉토리에서 상세 결과 확인")
    print("  2. law.go.kr에서 수동 검증")
    print("  3. 불일치 항목 분석")
    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="법순이 시나리오 테스트 실행기",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python tests/run_scenarios.py                    # 시나리오 목록
  python tests/run_scenarios.py --pilot            # 파일럿 테스트
  python tests/run_scenarios.py --run basic-01     # 특정 시나리오
  python tests/run_scenarios.py --run-category 02  # 카테고리별
        """,
    )

    parser.add_argument(
        "--run",
        metavar="ID",
        help="특정 시나리오 ID 실행 (예: basic-01)",
    )
    parser.add_argument(
        "--run-category",
        metavar="PREFIX",
        help="카테고리 접두사로 실행 (예: 01, 02)",
    )
    parser.add_argument(
        "--pilot",
        action="store_true",
        help="파일럿 테스트 (3개 핵심 시나리오)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="시나리오 목록만 출력",
    )

    args = parser.parse_args()

    # 시나리오 로드
    scenarios = load_all_scenarios()

    if not scenarios:
        print("⚠️  시나리오 파일이 없습니다.")
        print(f"   경로: {SCENARIOS_DIR}")
        sys.exit(1)

    # 실행
    if args.pilot:
        results = run_pilot_test(scenarios)
        print_summary(results)
    elif args.run:
        category, scenario = find_scenario(scenarios, args.run)
        if scenario:
            results = [run_scenario(category, scenario)]
            save_results(results, f"single_{args.run}")
            print_summary(results)
        else:
            print(f"⚠️  시나리오 '{args.run}'를 찾을 수 없습니다.")
            list_scenarios(scenarios)
    elif args.run_category:
        results = run_category(scenarios, args.run_category)
        if results:
            print_summary(results)
    else:
        # 기본: 목록 출력
        list_scenarios(scenarios)
        print("사용법:")
        print("  python tests/run_scenarios.py --pilot          # 파일럿 테스트")
        print("  python tests/run_scenarios.py --run <ID>       # 특정 시나리오")
        print("  python tests/run_scenarios.py --run-category 01  # 카테고리별")


if __name__ == "__main__":
    main()
