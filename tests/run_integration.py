#!/usr/bin/env python3
"""
법순이 통합 테스트 - Claude CLI 기반

claude -p로 실제 질문을 던지고 응답을 파일로 저장.
저장된 응답은 수동으로 검토/평가.

Usage:
    python tests/run_integration.py --pilot              # 파일럿 3개
    python tests/run_integration.py --run basic-01       # 특정 시나리오
    python tests/run_integration.py --category 01        # 카테고리별
    python tests/run_integration.py --all                # 전체 (비용 주의!)
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


def load_all_scenarios():
    """모든 시나리오 파일 로드"""
    scenarios = {}
    for yaml_file in sorted(SCENARIOS_DIR.glob("*.yaml")):
        with open(yaml_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            category_name = yaml_file.stem
            scenarios[category_name] = data
    return scenarios


def find_scenario(scenarios, scenario_id):
    """ID로 시나리오 찾기"""
    for category_name, data in scenarios.items():
        for scenario in data.get("scenarios", []):
            if scenario.get("id") == scenario_id:
                return category_name, scenario
    return None, None


def run_claude_p(question, timeout=300):
    """claude -p 실행"""
    cmd = [
        "claude", "-p", question,
        "--output-format", "json"
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=PROJECT_ROOT,
        )

        if result.returncode == 0:
            try:
                response = json.loads(result.stdout)
                return {
                    "success": True,
                    "result": response.get("result", ""),
                    "cost_usd": response.get("total_cost_usd", 0),
                    "duration_ms": response.get("duration_ms", 0),
                    "num_turns": response.get("num_turns", 0),
                    "raw": response,
                }
            except json.JSONDecodeError:
                return {
                    "success": True,
                    "result": result.stdout,
                    "cost_usd": 0,
                    "raw": result.stdout,
                }
        else:
            return {
                "success": False,
                "error": result.stderr or "Unknown error",
                "returncode": result.returncode,
            }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"Timeout ({timeout}s)",
        }
    except FileNotFoundError:
        return {
            "success": False,
            "error": "claude CLI not found. Is Claude Code installed?",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def run_scenario(category_name, scenario):
    """단일 시나리오 실행"""
    sid = scenario.get("id", "unknown")
    name = scenario.get("name", "이름 없음")
    question = scenario.get("question", "").strip()
    persona = scenario.get("persona", "")
    context = scenario.get("context", "").strip()
    expected = scenario.get("expected", {})

    print(f"\n{'─' * 60}")
    print(f"🧪 [{sid}] {name}")
    print(f"   👤 {persona}")
    print(f"{'─' * 60}")
    print(f"📝 질문: {question[:80]}...")
    print(f"\n⏳ claude -p 실행 중...")

    response = run_claude_p(question)

    if response["success"]:
        cost = response.get("cost_usd", 0)
        duration = response.get("duration_ms", 0) / 1000
        print(f"✅ 성공 (${cost:.4f}, {duration:.1f}s)")

        # 응답 미리보기
        result_text = response.get("result", "")
        preview = result_text[:300].replace("\n", " ")
        print(f"\n📄 응답 미리보기:\n   {preview}...")
    else:
        print(f"❌ 실패: {response.get('error', 'Unknown')}")

    return {
        "id": sid,
        "name": name,
        "category": category_name,
        "persona": persona,
        "context": context,
        "question": question,
        "expected": expected,
        "response": response,
        "timestamp": datetime.now().isoformat(),
    }


def save_results(results, prefix="integration"):
    """결과 저장 - Markdown + JSON"""
    RESULTS_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON 저장 (전체 데이터)
    json_path = RESULTS_DIR / f"{prefix}_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Markdown 저장 (검토용)
    md_path = RESULTS_DIR / f"{prefix}_{timestamp}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# 법순이 통합 테스트 결과\n\n")
        f.write(f"**실행 시각**: {timestamp}\n\n")

        total_cost = sum(
            r.get("response", {}).get("cost_usd", 0)
            for r in results
        )
        success_count = sum(
            1 for r in results
            if r.get("response", {}).get("success", False)
        )

        f.write(f"**요약**: {success_count}/{len(results)} 성공, 총 비용 ${total_cost:.4f}\n\n")
        f.write("---\n\n")

        for r in results:
            sid = r.get("id", "?")
            name = r.get("name", "")
            persona = r.get("persona", "")
            question = r.get("question", "")
            expected = r.get("expected", {})
            response = r.get("response", {})

            f.write(f"## [{sid}] {name}\n\n")
            f.write(f"**페르소나**: {persona}\n\n")
            f.write(f"**질문**:\n> {question}\n\n")

            if expected:
                f.write(f"**기대 요소**:\n")
                if expected.get("law_name"):
                    f.write(f"- 법령: {expected['law_name']}\n")
                if expected.get("contains_keywords"):
                    f.write(f"- 키워드: {', '.join(expected['contains_keywords'])}\n")
                f.write("\n")

            if response.get("success"):
                result_text = response.get("result", "")
                cost = response.get("cost_usd", 0)
                f.write(f"**응답** (${cost:.4f}):\n\n")
                f.write(f"```\n{result_text}\n```\n\n")
            else:
                f.write(f"**오류**: {response.get('error', 'Unknown')}\n\n")

            f.write(f"**검토 결과**: [ ] 정확 / [ ] 부분 정확 / [ ] 오류 / [ ] 환각\n\n")
            f.write(f"**코멘트**:\n\n")
            f.write("---\n\n")

    print(f"\n📄 결과 저장:")
    print(f"   JSON: {json_path}")
    print(f"   검토용 MD: {md_path}")

    return json_path, md_path


def print_summary(results):
    """결과 요약"""
    print("\n" + "=" * 60)
    print("📊 테스트 결과 요약")
    print("=" * 60)

    total = len(results)
    success = sum(
        1 for r in results
        if r.get("response", {}).get("success", False)
    )
    total_cost = sum(
        r.get("response", {}).get("cost_usd", 0)
        for r in results
    )

    print(f"   실행: {total}개")
    print(f"   성공: {success}개")
    print(f"   실패: {total - success}개")
    print(f"   총 비용: ${total_cost:.4f}")

    print("\n" + "─" * 60)
    print("다음 단계:")
    print("  1. results/*.md 파일을 열어 응답 검토")
    print("  2. 각 시나리오별 '검토 결과' 체크")
    print("  3. 문제 있는 응답에 코멘트 추가")
    print("=" * 60 + "\n")


def run_pilot(scenarios):
    """파일럿 테스트"""
    pilot_ids = ["basic-01", "admrul-01", "edge-01"]

    print("\n" + "=" * 60)
    print("🚀 파일럿 통합 테스트")
    print("   claude -p로 3개 핵심 시나리오 실행")
    print("=" * 60)

    results = []
    for sid in pilot_ids:
        category, scenario = find_scenario(scenarios, sid)
        if scenario:
            result = run_scenario(category, scenario)
            results.append(result)

    save_results(results, "pilot")
    print_summary(results)
    return results


def run_category(scenarios, category_prefix):
    """카테고리별 실행"""
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
        print_summary(results)

    return results


def run_all(scenarios):
    """전체 실행 (비용 주의!)"""
    total_count = sum(
        len(data.get("scenarios", []))
        for data in scenarios.values()
    )

    print("\n" + "=" * 60)
    print(f"⚠️  전체 테스트 실행: {total_count}개 시나리오")
    print(f"   예상 비용: ${total_count * 0.02:.2f} ~ ${total_count * 0.05:.2f}")
    print("=" * 60)

    confirm = input("\n계속하시겠습니까? (y/N): ")
    if confirm.lower() != "y":
        print("취소됨.")
        return []

    results = []
    for category_name, data in scenarios.items():
        print(f"\n{'=' * 60}")
        print(f"📁 {data.get('name', category_name)}")
        print("=" * 60)

        for scenario in data.get("scenarios", []):
            result = run_scenario(category_name, scenario)
            results.append(result)

    save_results(results, "all")
    print_summary(results)
    return results


def main():
    parser = argparse.ArgumentParser(
        description="법순이 통합 테스트 - Claude CLI 기반",
    )

    parser.add_argument("--pilot", action="store_true", help="파일럿 3개")
    parser.add_argument("--run", metavar="ID", help="특정 시나리오")
    parser.add_argument("--category", metavar="PREFIX", help="카테고리별 (01, 02...)")
    parser.add_argument("--all", action="store_true", help="전체 (비용 주의!)")

    args = parser.parse_args()

    scenarios = load_all_scenarios()

    if args.pilot:
        run_pilot(scenarios)
    elif args.run:
        category, scenario = find_scenario(scenarios, args.run)
        if scenario:
            results = [run_scenario(category, scenario)]
            save_results(results, f"single_{args.run}")
            print_summary(results)
        else:
            print(f"시나리오 '{args.run}'를 찾을 수 없습니다.")
    elif args.category:
        run_category(scenarios, args.category)
    elif args.all:
        run_all(scenarios)
    else:
        print("사용법:")
        print("  python tests/run_integration.py --pilot        # 파일럿 3개")
        print("  python tests/run_integration.py --run basic-01 # 특정 시나리오")
        print("  python tests/run_integration.py --category 01  # 카테고리별")
        print("  python tests/run_integration.py --all          # 전체")


if __name__ == "__main__":
    main()
