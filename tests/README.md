# 법순이 시나리오 테스트

법순이 스킬의 실제 사용성을 검증하는 시나리오 테스트입니다.

## 테스트 목적

- **정확도 검증**: 법령/판례 검색 결과가 실제와 일치하는지
- **완전성 검증**: 관련 행정규칙, 시행령 등을 누락 없이 안내하는지
- **환각 방지**: 존재하지 않는 법령/판례를 생성하지 않는지
- **실용성 검증**: 실무자가 활용할 수 있는 수준의 정보를 제공하는지

## 시나리오 카테고리

| 파일 | 카테고리 | 시나리오 수 | 설명 |
|------|----------|------------|------|
| `01_basic_law.yaml` | 기본 법령 검색 | 6개 | 조문 확인, 시행일 조회 |
| `02_admin_rules.yaml` | 행정규칙 연계 | 6개 | 고시/훈령 검색 (차별화 기능) |
| `03_case_law.yaml` | 판례 검색 | 6개 | 대법원/하급심 판례 |
| `04_temporal.yaml` | 시간적 정확성 | 5개 | 개정 이력, 미시행 법령 |
| `05_legislation.yaml` | 국회 의안 | 5개 | 개정안 추적, 계류 법안 |
| `06_complex.yaml` | 복합 실무 | 6개 | 다중 법령 종합 검토 |
| `07_edge_cases.yaml` | 엣지 케이스 | 8개 | 환각 방지, 예외 처리 |
| `08_policy_trends.yaml` | 정책 동향 | 6개 | 정부 집행 스탠스 파악 |
| `09_tricky_cases.yaml` | 함정 케이스 | 12개 | 폐지법령, 법령명 혼동, 조문 함정 |
| `10_practical_traps.yaml` | 실무 트랩 | 12개 | 판례 해석, 행정해석 필수 사례 |
| `11_domain_specific.yaml` | 업종별 | 12개 | 부동산, 세금, 형사, 창업 등 |
| `12_boundary_cases.yaml` | 경계 케이스 | 12개 | 외국법, 범위 외 질문, 에러 처리 |
| `13_contract_review.yaml` | 계약서 검토 보조 | 12개 | 영문/국문 계약 한국법 레퍼런스 |

**총 108개 시나리오**

## 사용법

```bash
# 시나리오 목록 확인
python tests/run_scenarios.py

# 파일럿 테스트 (핵심 3개)
python tests/run_scenarios.py --pilot

# 특정 시나리오 실행
python tests/run_scenarios.py --run basic-01

# 카테고리별 실행
python tests/run_scenarios.py --run-category 02
```

## 파일럿 테스트

처음 테스트할 때는 `--pilot` 옵션으로 3개 핵심 시나리오를 먼저 실행:

1. **basic-01**: 민법 제750조 조회 (기본 법령 검색)
2. **admrul-01**: 개인정보 유출 과징금 기준 (행정규칙 연계)
3. **edge-01**: 존재하지 않는 판례 요청 (환각 방지)

## 검증 방법

### 1단계: 자동 실행
```bash
python tests/run_scenarios.py --pilot
```

### 2단계: 결과 확인
```bash
# 결과 파일 확인
cat tests/results/pilot_*.json
```

### 3단계: 수동 검증
- [국가법령정보센터](https://law.go.kr)에서 조문 확인
- [대법원 종합법률정보](https://glaw.scourt.go.kr)에서 판례 확인
- 생성된 링크 클릭하여 유효성 검사

### 4단계: 크로스체크
- Claude/ChatGPT에서 법순이 없이 동일 질문
- 결과 비교하여 불일치 항목 분석

## 결과 파일 구조

```json
{
  "id": "basic-01",
  "name": "민법 불법행위 조항 확인",
  "question": "민법 제750조 불법행위 내용 확인해줘",
  "expected": { ... },
  "command_results": [
    {
      "command": "python .claude/skills/.../fetch_law.py exact \"민법\"",
      "result": {
        "success": true,
        "stdout": "...",
        "stderr": ""
      }
    }
  ],
  "timestamp": "2024-12-07T..."
}
```

## 평가 메트릭

| 메트릭 | 설명 | 목표 |
|--------|------|------|
| 조문 정확도 | 조문 내용 일치율 | ≥95% |
| 시행일 정확도 | 시행일 정보 정확성 | ≥90% |
| 행정규칙 연계율 | 고시/훈령 포함률 | ≥80% |
| 환각률 | 허위 정보 생성률 | ≤5% |
| 링크 유효성 | URL 작동률 | 100% |

## 시나리오 추가

새 시나리오는 `scenarios/` 디렉토리에 YAML 형식으로 추가:

```yaml
scenarios:
  - id: new-01
    name: 시나리오 이름
    persona: 사용자 유형
    context: |
      사용 상황 설명
    question: "사용자 질문"
    expected:
      law_name: 관련 법령
      contains_keywords:
        - 키워드1
        - 키워드2
    command: |
      python .claude/skills/beopsuny/scripts/fetch_law.py ...
```
