# 법순이 (Beopsuny)

> **AI가 한국 법령을 정확하게 답변하도록 돕는 스킬**

[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Scenarios](https://img.shields.io/badge/Test_Scenarios-96-orange.svg)](tests/scenarios/)

Claude Code, OpenAI Codex, Gemini CLI, Cursor 등에서 **국가법령정보센터 API**를 활용해 정확한 법령 정보를 제공합니다.

---

## 💡 왜 법순이가 필요한가요?

일반 AI는 법률 질문에 **환각(hallucination)** 문제가 있습니다:

| 문제 | 예시 |
|------|------|
| 폐지된 법령 인용 | "증권거래법 제XX조..." → 2009년 폐지됨 |
| 잘못된 조문 번호 | "근로기준법 제34조(퇴직금)..." → 2012년 삭제됨 |
| 과거 기준 답변 | "최저임금 9,860원..." → 2024년 기준 |
| 법령명 혼동 | "노동법 제X조..." → "노동법"이라는 법률은 없음 |

**법순이는 실시간 API로 이 문제를 해결합니다:**

```
❌ 일반 AI: "증권거래법 제188조에 따르면 내부자거래는..."
✅ 법순이:  "자본시장법 제174조에 따르면..." + law.go.kr 링크
```

---

## 🎬 30초 예시

**질문**: "2025년 최저임금이 얼마야?"

```bash
# AI가 법순이 스킬로 자동 조회
python scripts/fetch_law.py search "최저임금" --type admrul
```

**결과**:
> 2025년 최저시급은 **10,030원**입니다.
> 📎 출처: [최저임금위원회 고시 제2024-1호](https://law.go.kr/...)

---

## ✨ 주요 기능

| 기능 | 설명 | 건수 |
|------|------|------|
| **법령 검색** | 법률, 시행령, 시행규칙 | ~5,500 |
| **행정규칙** | 고시, 훈령, 예규 (실무 핵심!) | ~23,500 |
| **판례 검색** | 대법원/하급심 판결 | ~330,000 |
| **국회 의안** | 발의 법안, 개정안 추적 | 실시간 |
| **정책 동향** | 부처 보도자료, 법령해석례 | 실시간 |

---

## 🚀 빠른 시작

### 1. 저장소 생성

GitHub에서 **"Use this template"** → 새 레포지토리 생성

### 2. API 키 발급

| API | 발급처 | 필수 |
|-----|--------|------|
| 국가법령정보 OC 코드 | [open.law.go.kr](https://open.law.go.kr) | ✅ |
| 열린국회정보 API 키 | [open.assembly.go.kr](https://open.assembly.go.kr) | 선택 |

> **OC 코드**: 가입 이메일의 @ 앞부분 (예: `user@gmail.com` → `user`)

### 3. 환경변수 설정

```bash
export BEOPSUNY_OC_CODE="your_oc_code"
export BEOPSUNY_ASSEMBLY_API_KEY="your_api_key"  # 선택
```

<details>
<summary>📁 또는 설정 파일 사용 (로컬 개발용)</summary>

```bash
cp .claude/skills/beopsuny/config/settings.yaml.example \
   .claude/skills/beopsuny/config/settings.yaml
# settings.yaml에 API 키 입력
```

</details>

### 4. 사용 시작

```bash
# 법령 검색
python scripts/fetch_law.py exact "민법"

# 판례 검색
python scripts/fetch_law.py cases "손해배상"

# 행정규칙 (고시/훈령)
python scripts/fetch_law.py search "과징금" --type admrul
```

---

## 📖 상세 사용법

### 법령 검색

```bash
python scripts/fetch_law.py exact "상법"              # 정확한 법령명
python scripts/fetch_law.py search "개인정보" --type law  # 키워드 검색
```

### 행정규칙 검색 (고시/훈령/예규)

> 💡 **실무 팁**: 법률은 큰 틀만 정하고, 구체적 기준은 행정규칙에서 정합니다.

```bash
python scripts/fetch_law.py search "개인정보" --type admrul
python scripts/fetch_law.py search "과징금 부과기준" --type admrul
```

### 판례 검색

```bash
python scripts/fetch_law.py cases "불법행위 손해배상"
python scripts/fetch_law.py cases "통상임금"
```

<details>
<summary>더 많은 명령어</summary>

### 정책 동향

```bash
python scripts/fetch_policy.py rss ftc                   # 공정위 보도자료
python scripts/fetch_policy.py rss moel --keyword 임금   # 고용부 + 필터
python scripts/fetch_policy.py interpret "해고"          # 법령해석례
```

### 국회 의안

```bash
python scripts/fetch_bill.py track "상법"        # 개정안 추적
python scripts/fetch_bill.py recent --days 30    # 최근 발의안
```

### 법령 다운로드 및 링크

```bash
python scripts/fetch_law.py fetch --name "민법"
python scripts/gen_link.py law "민법" --article 750
python scripts/gen_link.py case "2022다12345"
```

</details>

---

## 🤖 AI 도구 통합

| 도구 | 설정 파일 | 사용법 |
|------|----------|--------|
| **Claude Code** | CLAUDE.md (자동 로드) | `git clone` 후 바로 사용 |
| **OpenAI Codex** | AGENTS.md (자동 로드) | `git clone` 후 바로 사용 |
| **Gemini CLI** | GEMINI.md → AGENTS.md | `git clone` 후 바로 사용 |
| **Cursor** | AGENTS.md (v1.6+) | 프로젝트 열면 자동 인식 |

<details>
<summary>⚠️ Windows 사용자 안내</summary>

이 프로젝트는 `CLAUDE.md`, `GEMINI.md`가 `AGENTS.md`로의 symlink입니다.

```powershell
# 방법 1: symlink 활성화
git config --global core.symlinks true
# 관리자 권한 터미널에서 clone

# 방법 2: 파일 복사
copy AGENTS.md CLAUDE.md
copy AGENTS.md GEMINI.md
```

</details>

<details>
<summary>🌏 해외에서 사용하기</summary>

한국 정부 API는 해외 IP를 차단합니다. 게이트웨이 설정이 필요합니다.

```bash
export BEOPSUNY_GATEWAY_URL='https://your-cors-proxy.workers.dev'
export BEOPSUNY_GATEWAY_API_KEY='your-api-key'  # 선택
```

**무료 게이트웨이 구축:**
1. [Zibri/cloudflare-cors-anywhere](https://github.com/Zibri/cloudflare-cors-anywhere) fork
2. Cloudflare Workers 배포
3. URL을 `BEOPSUNY_GATEWAY_URL`에 설정

</details>

---

## 🧪 테스트

96개 시나리오로 법순이의 정확성을 검증합니다.

```bash
python tests/run_scenarios.py              # 시나리오 목록
python tests/run_scenarios.py --pilot      # 핵심 3개 테스트
python tests/run_scenarios.py --run basic-01  # 특정 시나리오
```

| 카테고리 | 시나리오 수 | 설명 |
|----------|-------------|------|
| 기본 사용 | 12 | 법령/판례 검색 기초 |
| 행정규칙 | 12 | 고시/훈령 검색 |
| 시간적 정확성 | 12 | 시행일, 개정 이력 |
| 함정 케이스 | 24 | 폐지법령, 법령명 혼동 |
| 업종별 | 12 | 부동산, 세금, 형사 등 |
| 경계 케이스 | 12 | 외국법, 범위 외 질문 |

자세한 내용: [tests/README.md](tests/README.md)

---

## 📁 프로젝트 구조

```
.
├── AGENTS.md                    # AI 에이전트 지침 (단일 소스)
├── CLAUDE.md -> AGENTS.md       # Claude Code용 (symlink)
├── GEMINI.md -> AGENTS.md       # Gemini CLI용 (symlink)
├── .claude/skills/beopsuny/
│   ├── SKILL.md                 # 상세 사용법
│   ├── scripts/                 # 실행 스크립트
│   ├── config/                  # 설정 파일
│   └── data/                    # 다운로드 데이터
├── tests/
│   ├── scenarios/               # 96개 테스트 시나리오
│   └── run_scenarios.py         # 테스트 실행기
└── README.md
```

---

## ⚖️ 법률 리서치 원칙

법순이를 사용하는 AI는 다음 원칙을 따릅니다:

1. **정확한 인용** - 구체적인 조문/판례 번호 명시
2. **검증 가능한 링크** - law.go.kr 직접 링크 제공
3. **시행일 확인** - 현행 여부와 시행일자 표시
4. **환각 방지** - 추측하지 않고, 모르면 "확인 필요" 명시
5. **면책 고지** - 정식 법률 자문은 변호사 상담 필요

---

## 🔗 참고 사이트

| 사이트 | URL | 용도 |
|--------|-----|------|
| 국가법령정보센터 | https://law.go.kr | 법령/판례 원문 |
| 열린국회정보 | https://open.assembly.go.kr | 국회 의안 API |
| 대법원 종합법률정보 | https://glaw.scourt.go.kr | 판례 원문 |
| 헌법재판소 | https://ccourt.go.kr | 헌재 결정문 |

---

## 📦 Claude Desktop 설치

```bash
python build_skill.py
```

생성된 `beopsuny-skill.zip`을 Claude Desktop Skills 메뉴에서 추가합니다.

> ⚠️ zip 파일에는 개인 API 키가 포함되므로 공유하지 마세요.

---

## 🤝 기여하기

버그 리포트, 기능 제안, PR을 환영합니다!

1. Fork
2. Feature branch 생성 (`git checkout -b feat/amazing-feature`)
3. Commit (`git commit -m 'Add amazing feature'`)
4. Push (`git push origin feat/amazing-feature`)
5. Pull Request 생성

---

## 📄 라이선스

MIT License - 자유롭게 사용, 수정, 배포할 수 있습니다.
