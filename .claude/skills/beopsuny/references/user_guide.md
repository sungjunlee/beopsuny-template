# 법순이 사용자 가이드

> 법순이의 모든 기능을 상세히 설명하는 가이드입니다.

## 목차

1. [설치 및 설정](#1-설치-및-설정)
2. [명령어 레퍼런스](#2-명령어-레퍼런스)
3. [체크리스트 활용](#3-체크리스트-활용)
4. [고급 워크플로우](#4-고급-워크플로우)
5. [문제 해결 (FAQ)](#5-문제-해결-faq)

---

## 1. 설치 및 설정

### 1.1 설치 방법

#### 방법 1: Plugin 설치 (권장)

Claude Code에서 바로 설치:

```bash
# Marketplace 등록
/plugin marketplace add sungjunlee/beopsuny-template

# 설치
/plugin install beopsuny
```

#### 방법 2: Template Fork

1. GitHub에서 **"Use this template"** 클릭
2. 새 레포지토리 생성
3. `git clone`으로 로컬에 복제

#### 방법 3: Claude Desktop (ZIP)

```bash
python build_skill.py
```

생성된 `beopsuny-skill.zip`을 Claude Desktop → Settings → Skills에서 추가합니다.

> ⚠️ zip 파일에는 개인 API 키가 포함되므로 공유하지 마세요.

### 1.2 API 키 발급

| API | 발급처 | 필수 | 용도 |
|-----|--------|------|------|
| 국가법령정보 OC 코드 | [open.law.go.kr](https://open.law.go.kr) | ✅ | 법령/판례 검색 |
| 열린국회정보 API 키 | [open.assembly.go.kr](https://open.assembly.go.kr) | 선택 | 국회 의안 조회 |

**OC 코드 확인**: 가입 이메일의 @ 앞부분 (예: `user@gmail.com` → `user`)

### 1.3 환경변수 설정

```bash
# 필수
export BEOPSUNY_OC_CODE="your_oc_code"

# 선택
export BEOPSUNY_ASSEMBLY_API_KEY="your_api_key"
```

또는 설정 파일 사용:

```bash
cp .claude/skills/beopsuny/config/settings.yaml.example \
   .claude/skills/beopsuny/config/settings.yaml
# settings.yaml에 API 키 입력
```

### 1.4 해외에서 사용하기

한국 정부 API는 해외 IP를 차단합니다. 게이트웨이 설정이 필요합니다.

```bash
export BEOPSUNY_GATEWAY_URL='https://your-cors-proxy.workers.dev'
export BEOPSUNY_GATEWAY_API_KEY='your-api-key'  # 선택
```

**무료 게이트웨이 구축:**
1. [Zibri/cloudflare-cors-anywhere](https://github.com/Zibri/cloudflare-cors-anywhere) fork
2. Cloudflare Workers에 배포
3. URL을 `BEOPSUNY_GATEWAY_URL`에 설정

---

## 2. 명령어 레퍼런스

> 스크립트 경로: `.claude/skills/beopsuny/scripts/`

### 2.1 법령 검색 (fetch_law.py)

#### 정확한 법령 검색

```bash
fetch_law.py exact "상법"                    # 정확한 법령명
fetch_law.py exact "상법" --with-admrul      # + 관련 행정규칙
fetch_law.py exact "민법" --with-decree      # + 시행령/시행규칙
```

#### 키워드 검색

```bash
fetch_law.py search "개인정보" --type law    # 법령에서 검색
fetch_law.py search "과징금" --type admrul   # 행정규칙에서 검색
fetch_law.py search "민법" --format json     # JSON 출력
```

#### 검색 대상 코드

| 코드 | 대상 | 설명 |
|------|------|------|
| `law` | 법령 | 법률, 대통령령, 부령 |
| `admrul` | 행정규칙 | 고시, 훈령, 예규 (실무 핵심!) |
| `prec` | 판례 | 대법원, 하급심 |
| `ordin` | 자치법규 | 조례, 규칙 |
| `expc` | 법령해석례 | 법제처 해석 |
| `detc` | 헌재결정례 | 헌법재판소 결정 |

### 2.2 판례 검색

```bash
fetch_law.py cases "손해배상"                          # 키워드 검색
fetch_law.py cases "해고" --court 대법원               # 법원 지정
fetch_law.py cases "통상임금" --from 20240101          # 날짜 필터
fetch_law.py cases "부당해고" --court 대법원 --from 20240101
```

### 2.3 법령/판례 다운로드

```bash
# 법령명으로 다운로드
fetch_law.py fetch --name "민법"
fetch_law.py fetch --name "민법" --with-decree  # 시행령 포함

# 판례 다운로드 (사건번호)
fetch_law.py fetch --case "2022다12345"

# ID로 직접 다운로드
fetch_law.py fetch --id <ID> --type <타입>
```

**타입별 다운로드 예시:**

| 타입 | 명령어 예시 |
|------|------------|
| 행정규칙 | `fetch --id 2100000259318 --type admrul` |
| 자치법규 | `fetch --id 2084665 --type ordin` |
| 법령해석례 | `fetch --id 311537 --type expc` |
| 헌재결정례 | `fetch --id 134954 --type detc` |
| 판례 | `fetch --id 237875 --type prec` |

### 2.4 개정 확인

```bash
fetch_law.py recent --days 30                           # 최근 30일 시행
fetch_law.py recent --from 20251101 --to 20251130       # 기간 지정
fetch_law.py recent --from 20251101 --date-type anc     # 공포일 기준
```

### 2.5 국회 의안 (fetch_bill.py)

```bash
fetch_bill.py track "상법"           # 개정안 추적
fetch_bill.py pending --keyword 민법  # 계류 의안
fetch_bill.py recent --days 30       # 최근 발의
```

### 2.6 정책 동향 (fetch_policy.py)

```bash
fetch_policy.py rss ftc --keyword 과징금   # 공정위 보도자료
fetch_policy.py rss moel --keyword 임금    # 고용부 보도자료
fetch_policy.py interpret "해고"          # 법령해석례
fetch_policy.py summary --days 7          # 종합 요약
```

**주요 부처 코드:**

| 부처 | 코드 | 관련 법령 |
|------|------|----------|
| 공정거래위원회 | `ftc` | 공정거래법, 하도급법 |
| 개인정보보호위원회 | `pipc` | 개인정보보호법 |
| 고용노동부 | `moel` | 근로기준법, 산재법 |
| 금융위원회 | `fsc` | 자본시장법 |

### 2.7 링크 생성 (gen_link.py)

```bash
gen_link.py law "민법" --article 750      # 민법 제750조 링크
gen_link.py case "2022다12345"           # 판례 링크
```

### 2.8 법령 비교 (compare_law.py)

```bash
# 두 버전의 법령 XML 파일 비교
compare_law.py data/raw/민법_이전.xml data/raw/민법_현행.xml --name 민법
```

**비교 워크플로우:**
1. `fetch_law.py fetch --name "민법"` → 현행 법령 다운로드
2. 연혁법령에서 이전 버전 다운로드 (law.go.kr 웹사이트)
3. `compare_law.py old.xml new.xml` → 변경 사항 비교

---

## 3. 체크리스트 활용

법적 점검사항을 체계적으로 확인할 수 있는 체크리스트를 제공합니다.

### 3.1 체크리스트 명령어

```bash
fetch_law.py checklist list                              # 체크리스트 목록
fetch_law.py checklist show startup                      # 스타트업 설립
fetch_law.py checklist show privacy_compliance           # 개인정보처리자 점검
fetch_law.py checklist show fair_trade                   # 공정거래 컴플라이언스
fetch_law.py checklist show startup --output startup.md  # 파일 저장
fetch_law.py checklist show startup --format json        # JSON 출력
```

### 3.2 제공 체크리스트

| 이름 | 내용 | 항목 수 |
|------|------|--------|
| `startup` | 스타트업 설립 체크리스트 | 11개 |
| `privacy_compliance` | 개인정보처리자 자가점검 | 12개 |
| `fair_trade` | 공정거래 컴플라이언스 | 12개 |
| `contract_review` | 계약서 검토 체크리스트 | 10개 |
| `labor_hr` | 노동/인사 컴플라이언스 | 12개 |
| `serious_accident` | 중대재해처벌법 점검 | 10개 |
| `investment_due_diligence` | 투자 실사 체크리스트 | 11개 |

### 3.3 체크리스트 구조

각 체크리스트는 다음 정보를 포함합니다:

- **task**: 점검 항목
- **laws**: 관련 법령 및 조문
- **notes**: 실무 가이드
- **deadline**: 기한 (해당 시)
- **condition**: 적용 조건
- **risk_level**: 위험도 (high/medium/low)
- **check_points**: 세부 확인사항

### 3.4 활용 예시

```bash
# 스타트업 설립 시
fetch_law.py checklist show startup

# 결과를 파일로 저장해서 팀과 공유
fetch_law.py checklist show startup --output 설립_체크리스트.md
```

---

## 4. 고급 워크플로우

### 4.1 법률 조사 9단계 워크플로우

법률 조사 요청 시 권장하는 체계적인 순서입니다.

| Phase | 작업 | 도구 |
|-------|------|------|
| 1 | 법령 조문 확인 | `fetch_law.py exact "{법령}"` |
| 2 | **행정규칙 확인** ⭐ | `fetch_law.py search --type admrul` |
| 3 | 개정 확인 | `fetch_law.py recent --days 30` |
| 4 | 법령해석례 | `fetch_policy.py interpret` |
| 5 | 부처 보도자료 | `fetch_policy.py rss {부처}` |
| 6 | **제재 동향** ⭐ | WebSearch |
| 7 | 전문매체 확인 | WebSearch |
| 8 | 판례 변경 확인 | WebSearch |
| 9 | 국회 개정안 | `fetch_bill.py track` |

### 4.2 행정규칙의 중요성

> 💡 **실무 팁**: 법률은 큰 틀만 정하고, **구체적 기준은 행정규칙**에서 정합니다.

예를 들어 "개인정보보호법 위반 과징금이 얼마인가?"라는 질문에:

- ❌ 법률만 보면: "전체 매출의 4% 이하" (막연함)
- ✅ 행정규칙까지 보면: 위반 유형별 구체적 산정 기준표

```bash
# 항상 행정규칙까지 확인
fetch_law.py exact "개인정보보호법"
fetch_law.py search "과징금 부과기준" --type admrul
```

### 4.3 WebSearch 활용 패턴

API로 얻기 어려운 최신 정보는 웹검색으로 보완합니다.

| 목적 | 검색 쿼리 템플릿 |
|------|-----------------|
| 제재 사례 | `"{법령} 과징금 2024 2025 site:lawtimes.co.kr"` |
| 정부 스탠스 | `"{부처} {법령} 제재 2025"` |
| 판례 변경 | `"{법령} 대법원 전원합의체 2024 2025"` |
| 법제처 해석 | `"{법령} 법제처 유권해석 2024 2025"` |

### 4.4 law_index.yaml 활용

자주 사용하는 행정규칙 ID가 미리 정리되어 있습니다.

```bash
# law_index.yaml에서 ID 확인 후 바로 다운로드
fetch_law.py fetch --id 2100000229342 --type admrul  # 개인정보 과징금 기준
```

**주요 ID:**

| 법령 | 행정규칙 | ID |
|------|----------|-----|
| 개인정보보호법 | 과징금_부과기준 | `2100000229342` |
| 개인정보보호법 | 안전성_확보조치 | `2100000265956` |
| 공정거래법 | 과징금_부과기준 | `2100000246412` |
| 최저임금법 | 2025년_고시 | `2100000245668` |

전체 목록: `config/law_index.yaml`

---

## 5. 문제 해결 (FAQ)

### Q1: API 호출이 실패합니다

**증상**: `Connection refused` 또는 `403 Forbidden`

**해결**:
1. OC 코드가 올바른지 확인 (이메일 @ 앞부분)
2. 해외에서 접속 중인지 확인 → 게이트웨이 설정 필요
3. API 일일 호출 한도 초과 여부 확인

### Q2: 검색 결과가 없습니다

**증상**: `No results found`

**해결**:
1. `exact` 대신 `search` 사용해보기 (부분 일치)
2. 법령 정식 명칭 확인 (예: "노동법" → "근로기준법")
3. 폐지된 법령인지 확인

### Q3: 행정규칙을 찾을 수 없습니다

**해결**:
1. `law_index.yaml`에서 ID 먼저 확인
2. 키워드를 다양하게 시도 (예: "과징금", "부과기준", "산정기준")
3. 법령명 + "고시" 또는 "훈령"으로 검색

### Q4: Windows에서 symlink 오류

**증상**: `CLAUDE.md`가 텍스트 파일로 보임

**해결**:
```powershell
# 방법 1: symlink 활성화 (관리자 권한 필요)
git config --global core.symlinks true

# 방법 2: 파일 복사
copy AGENTS.md CLAUDE.md
copy AGENTS.md GEMINI.md
```

### Q5: Claude Desktop에서 스킬이 인식 안됨

**해결**:
1. ZIP 파일 구조 확인 (루트에 `beopsuny/` 폴더가 있어야 함)
2. `SKILL.md`가 `beopsuny/SKILL.md` 경로에 있는지 확인
3. Claude Desktop 재시작

---

## 관련 문서

- [계약서 검토 가이드](contract_review_guide.md) - 계약서 검토 워크플로우
- [체크리스트 유지보수 가이드](../config/checklists/MAINTENANCE.md) - 체크리스트 관리

---

## 면책 고지

> ⚠️ 법순이는 법령 조회 및 1차 리서치 도구입니다.
> 최종 법률 판단은 반드시 **변호사와 상담**하세요.
