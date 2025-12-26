---
name: beopsuny
description: |
  법순이 - 한국 법령/판례 검색, 다운로드, 분석 도우미.
  법률 조문 확인, 판례 검색, 개정 확인, 시행령/시행규칙, 국회 의안 조회 시 자동 활성화.
  Korean law research assistant via National Law Information Center & Assembly APIs.
license: MIT
compatibility: |
  - Python 3.9+
  - 환경변수: BEOPSUNY_OC_CODE (필수, 국가법령정보센터 API)
  - 선택: BEOPSUNY_ASSEMBLY_API_KEY (국회 API)
  - 선택: BEOPSUNY_GATEWAY_URL (해외 사용 시)
metadata:
  # version follows project git tags (see CHANGELOG.md)
  author: "legal-stack"
  language: "ko"
  updated: "2025-12-26"
---

# Beopsuny (법순이)

국가법령정보센터 Open API를 활용한 한국 법령/판례 검색, 분석 스킬.

---

## 1. Overview (개요)

### 핵심 원칙 5가지

1. **정확한 인용 (Citation)**: 법령 "민법 제750조", 판례 "대법원 2023. 1. 12. 선고 2022다12345 판결"
2. **law.go.kr 링크 필수**: 모든 인용에 검증 가능한 링크 포함
3. **행정규칙 확인** ⭐: 법률은 큰 틀만, 구체적 기준/절차/과징금은 고시/훈령에서 규정
4. **시행일 확인**: 현행 여부 확인, 미시행 법령 명확히 표시 "⚠️ 미시행 (2026.1.1. 시행 예정)"
5. **환각 방지**: 조문/판례 번호 추측 금지, 모르면 "확인 필요" 명시

### 스킬 범위

**법순이가 하는 것:**
- 법령 조회 및 1차 리서치
- 조항 → 한국 법령 레퍼런스 제공
- 한국 강행규정, 약관규제법 등 효력 이슈 경고

**법순이 범위 외:**
| 업무 | 대안 |
|------|------|
| 계약서 자동분석/수정안 | Law.ai, 프릭스, 슈퍼로이어 |
| 판례 심층분석/트렌드 | 엘박스 AI, 빅케이스, 케이스노트 |
| 외국법 (GDPR, CCPA 등) | 외국법 전문가 상담 |
| 법률 자문/소송 전략 | 변호사 상담 |

### 면책 고지 (답변 마지막에 필수)

> ⚠️ **참고**: 이 정보는 일반적인 법률 정보 제공 목적이며, 구체적인 법률 문제는 변호사와 상담하시기 바랍니다.

---

## 2. Setup (환경 설정)

### API 키 설정

```bash
# 필수 (국가법령정보센터)
export BEOPSUNY_OC_CODE="your_oc_code"

# 선택 (국회 API)
export BEOPSUNY_ASSEMBLY_API_KEY="your_api_key"
```

또는 `config/settings.yaml`에 설정.

### 해외 접근 (게이트웨이)

```bash
export BEOPSUNY_GATEWAY_URL='https://your-gateway.example.com'
export BEOPSUNY_GATEWAY_API_KEY='your-api-key'
```

---

## 3. Core Workflows (핵심 워크플로우)

### 법률 조사 9단계 워크플로우 ⭐

법률 조사 요청 시 아래 순서대로 실행:

| Phase | 단계 | 확인 사항 | 도구 |
|-------|------|----------|------|
| **1차 소스** | 1 | 법령 조문 | `fetch_law.py exact "{법령}"` |
| | 2 | **행정규칙** ⭐ | law_index.yaml 우선, 없으면 `--type admrul` |
| | 3 | 개정 확인 | `recent --days 30` |
| **집행 동향** | 4 | 법령해석례 | `fetch_policy.py interpret` |
| | 5 | 보도자료 | `fetch_policy.py rss [부처]` |
| | 6 | **제재 동향** ⭐ | **WebSearch 필수** |
| **2차 검증** | 7 | 전문매체 | WebSearch `site:lawtimes.co.kr` |
| | 8 | 판례 변경 | WebSearch `"전원합의체" 2024 2025` |
| | 9 | 국회 개정안 | `fetch_bill.py track` |

### Phase 2: 행정규칙 (가장 중요) ⭐

```bash
# 1. law_index.yaml에서 ID 확인 (빠름)
# 2. 없으면 API 검색
fetch_law.py search "과징금" --type admrul
fetch_law.py fetch --id {ID} --type admrul
```

### Phase 6-8: WebSearch 템플릿 ⭐

```
# 제재 동향 (Phase 6)
"{법령명} 과징금 2024 2025 site:lawtimes.co.kr"
"{부처명} {법령명} 제재 2025"

# 판례 변경 (Phase 8)
"{법령명} 대법원 전원합의체 2024 2025"
```

### 정부 집행 스탠스 파악

> 법령 조문보다 **정부의 실제 집행 스탠스**가 실무에 더 중요

**주요 기관 RSS:**
| 기관 | 코드 | 관련 법령 |
|------|------|----------|
| 공정거래위원회 | `ftc` | 공정거래법, 하도급법 |
| 고용노동부 | `moel` | 근로기준법, 산업안전보건법 |
| 금융위원회 | `fsc` | 자본시장법 |
| 개인정보보호위원회 | `pipc` | 개인정보보호법 |

---

## 4. Commands Reference (명령어)

> 스크립트 경로: `.claude/skills/beopsuny/scripts/`

### 검색 대상 코드

| 코드 | 대상 | 설명 |
|------|------|------|
| `law` | 법령 | 법률, 대통령령, 부령 |
| `admrul` | **행정규칙** ⭐ | 고시, 훈령, 예규 (실무 핵심) |
| `prec` | 판례 | 대법원, 하급심 |
| `ordin` | 자치법규 | 조례, 규칙 |
| `expc` | 법령해석례 | 법제처 해석 |
| `detc` | 헌재결정례 | 헌법재판소 결정 |

### 법령 검색/다운로드

```bash
# 정확한 법령 검색
fetch_law.py exact "상법"
fetch_law.py exact "상법" --with-admrul      # + 관련 행정규칙

# 키워드 검색
fetch_law.py search "개인정보" --type law
fetch_law.py search "과징금" --type admrul

# 다운로드
fetch_law.py fetch --name "민법"
fetch_law.py fetch --name "민법" --with-decree  # 시행령 포함
fetch_law.py fetch --id <ID> --type <타입>      # ID로 다운로드
```

### 판례 검색

```bash
fetch_law.py cases "손해배상"
fetch_law.py cases "해고" --court 대법원 --from 20240101
fetch_law.py fetch --case "2022다12345"         # 사건번호로 다운로드
```

### 개정 확인

```bash
fetch_law.py recent --days 30                           # 최근 시행
fetch_law.py recent --from 20251101 --to 20251130       # 기간 지정
fetch_law.py recent --from 20251101 --date-type anc     # 공포일 기준
```

### 국회 의안

```bash
fetch_bill.py track "상법"           # 개정안 추적
fetch_bill.py pending --keyword 민법  # 계류 의안
fetch_bill.py recent --days 30       # 최근 발의
```

### 정책 동향

```bash
fetch_policy.py rss ftc --keyword 과징금   # 공정위 보도자료
fetch_policy.py interpret "해고"          # 법령해석례
fetch_policy.py summary --days 7          # 종합 요약
```

### 링크 생성

```bash
gen_link.py law "민법" --article 750
gen_link.py case "2022다12345"
```

### 체크리스트

```bash
fetch_law.py checklist list                              # 목록 보기
fetch_law.py checklist show startup                      # 스타트업 설립
fetch_law.py checklist show privacy_compliance           # 개인정보처리자
fetch_law.py checklist show fair_trade                   # 공정거래
fetch_law.py checklist show startup --output startup.md  # 파일 저장
```

**제공 체크리스트:** startup, privacy_compliance, fair_trade, contract_review, labor_hr, serious_accident, investment_due_diligence

> 체크리스트 위치: `assets/checklists/*.yaml`

### 법령 개정 비교

```bash
compare_law.py data/raw/민법_이전.xml data/raw/민법_현행.xml --name 민법
```

---

## 5. Use Cases (활용 사례)

### 계약서 검토 보조

> Claude + 법순이 하이브리드로 **계약서의 한국법 관점 검토** 지원

**지원 범위:**
| 계약서 유형 | 제공 기능 |
|------------|----------|
| **한국어 계약서** | 조항 → 한국 법령 레퍼런스, 효력 이슈 경고 |
| **영문 계약서** | 위 기능 + 법률 용어 영한 번역, 뉘앙스 차이 설명 |

**레퍼런스 파일:**
| 파일 | 내용 |
|------|------|
| `assets/clause_references.yaml` | 조항-법령 매핑 DB (30개 조항) |
| `assets/legal_terms.yaml` | 영한 법률용어 사전 (100개 용어) |
| `references/contract_review_guide.md` | 검토 워크플로우 플레이북 |

**횡단 이슈 체크 (국제거래/하도급):**
```bash
# 국제거래 - 원천징수
fetch_law.py exact "법인세법"        # 제93조 국내원천소득

# 하도급 관계
fetch_law.py exact "하도급거래 공정화에 관한 법률"
```

> ⚠️ 본 기능은 **초벌 검토 보조**용입니다. 최종 검토는 **변호사와 상담**하세요.

### 해외 진출 시 확인 가이드

해외직접투자, 전략물자 수출, 국제조세 등 **한국법에서 확인해야 할 사항**:

| 영역 | 확인할 법령 | 기관 |
|------|------------|------|
| 해외직접투자 | 외국환거래법 | 지정거래외국환은행 |
| 전략물자 수출 | 대외무역법 | yestrade.go.kr |
| 이전가격/국제조세 | 국조법 | 국세청 |
| 산업기술 보호 | 산업기술유출방지법 | 산업부 |
| 개인정보 국외이전 | 개인정보보호법 | 개인정보보호위 |

> 상세 가이드: `references/international_guide.md`

### 주간 규제 점검 패턴

```bash
# 1. 최근 시행/공포 법령
fetch_law.py recent --days 7
fetch_law.py recent --days 7 --date-type anc

# 2. 관심 법령 개정안
fetch_bill.py track "개인정보보호법"
fetch_bill.py track "공정거래법"

# 3. 부처 동향
fetch_policy.py rss pipc
fetch_policy.py rss ftc
```

---

## 6. Resources (참고 자료)

### 상세 레퍼런스

| 문서 | 내용 |
|------|------|
| [Quick Reference](references/quick-reference.md) | 자주 쓰는 명령어 치트시트 |
| [External Sites](references/external-sites.md) | 외부 참고 사이트 목록 |
| [Contract Review Guide](references/contract_review_guide.md) | 계약서 검토 워크플로우 |
| [International Guide](references/international_guide.md) | 해외 진출 시 확인 가이드 |
| [User Guide](references/user_guide.md) | 사용자 가이드 |

### 데이터 파일

| 파일 | 내용 |
|------|------|
| `assets/law_index.yaml` | 주요 법령-행정규칙 ID 매핑 |
| `assets/legal_terms.yaml` | 영한 법률용어 사전 |
| `assets/clause_references.yaml` | 조항-법령 매핑 DB |
| `assets/checklists/*.yaml` | 법적 체크리스트 7종 |

---

## Instructions for Claude

### 법령 검색 시
1. `exact` 사용 (search는 부분 일치 → "상법" 검색 시 "보상법" 포함)
2. 시행일 반드시 확인, 미시행 법령 명확히 표시
3. 이미 다운로드된 파일 있으면 재사용 (`data/raw/` 확인)

### 행정규칙 ⭐ IMPORTANT
> 법률만 보면 안 됩니다! 구체적 기준/절차/과징금은 행정규칙에 있습니다.

- 실무 질문 시 `--type admrul` 검색 필수
- 법률 → 시행령 → 행정규칙 순서로 체계적 검토

### 출력 형식
```markdown
## 민법 제750조 (불법행위의 내용)
> 고의 또는 과실로 인한 위법행위로 타인에게 손해를 가한 자는...

- **시행일**: 2025. 1. 31.
- **링크**: https://www.law.go.kr/법령/민법/제750조
```
