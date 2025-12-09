# 법순이 (Beopsuny)

> **AI가 한국 법령을 정확하게 답변하도록 돕는 스킬**

[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Scenarios](https://img.shields.io/badge/Test_Scenarios-111-orange.svg)](tests/scenarios/)

Claude Code, OpenAI Codex, Gemini CLI, Cursor 등에서 **국가법령정보센터 API**를 활용해 정확한 법령 정보를 제공합니다.

---

## 왜 법순이가 필요한가요?

일반 AI는 법률 질문에 **환각(hallucination)** 문제가 있습니다:

| 문제 | 예시 |
|------|------|
| 폐지된 법령 인용 | "증권거래법 제XX조..." → 2009년 폐지됨 |
| 잘못된 조문 번호 | "근로기준법 제34조(퇴직금)..." → 2012년 삭제됨 |
| 법령명 혼동 | "노동법 제X조..." → "노동법"이라는 법률은 없음 |

**법순이는 실시간 API로 이 문제를 해결합니다:**

```
❌ 일반 AI: "증권거래법 제188조에 따르면 내부자거래는..."
✅ 법순이:  "자본시장법 제174조에 따르면..." + law.go.kr 링크
```

---

## 주요 기능

| 기능 | 설명 | 건수 |
|------|------|------|
| **법령 검색** | 법률, 시행령, 시행규칙 | ~5,500 |
| **행정규칙** | 고시, 훈령, 예규 (실무 핵심!) | ~23,500 |
| **판례 검색** | 대법원/하급심 판결 | ~330,000 |
| **체크리스트** | 스타트업 설립, 개인정보, 공정거래 등 | 7종 |
| **국회 의안** | 발의 법안, 개정안 추적 | 실시간 |
| **계약서 검토** | 조항-법령 매핑, 영한 법률용어 | 30조항/100용어 |

---

## 빠른 시작

### 1. 설치

**방법 A: Plugin 설치 (권장)**

```bash
/plugin marketplace add sungjunlee/beopsuny-template
/plugin install beopsuny
```

**방법 B: Template Fork**

GitHub에서 **"Use this template"** → 새 레포지토리 생성

### 2. API 키 설정

[open.law.go.kr](https://open.law.go.kr)에서 회원가입 후 OC 코드 확인 (이메일 @ 앞부분)

```bash
export BEOPSUNY_OC_CODE="your_oc_code"
```

### 3. 사용

```bash
# 법령 검색
python scripts/fetch_law.py exact "민법"

# 행정규칙 (고시/훈령) - 실무 핵심!
python scripts/fetch_law.py search "과징금" --type admrul

# 판례 검색
python scripts/fetch_law.py cases "손해배상"

# 체크리스트
python scripts/fetch_law.py checklist show startup
```

> 📖 **상세 가이드**: [사용자 가이드](.claude/skills/beopsuny/docs/user_guide.md)

---

## 문서

| 문서 | 내용 |
|------|------|
| [📖 사용자 가이드](.claude/skills/beopsuny/docs/user_guide.md) | 설치, 명령어 레퍼런스, 체크리스트, FAQ |
| [📝 계약서 검토 가이드](.claude/skills/beopsuny/docs/contract_review_guide.md) | 계약서 검토 워크플로우 |
| [🧪 테스트 가이드](tests/README.md) | 111개 시나리오 테스트 |

---

## AI 도구 통합

| 도구 | 설정 파일 | 사용법 |
|------|----------|--------|
| **Claude Code** | CLAUDE.md (자동 로드) | `git clone` 후 바로 사용 |
| **OpenAI Codex** | AGENTS.md (자동 로드) | `git clone` 후 바로 사용 |
| **Gemini CLI** | GEMINI.md → AGENTS.md | `git clone` 후 바로 사용 |
| **Cursor** | AGENTS.md (v1.6+) | 프로젝트 열면 자동 인식 |

---

## 법률 리서치 원칙

법순이를 사용하는 AI는 다음 원칙을 따릅니다:

1. **정확한 인용** - 구체적인 조문/판례 번호 명시
2. **검증 가능한 링크** - law.go.kr 직접 링크 제공
3. **시행일 확인** - 현행 여부와 시행일자 표시
4. **환각 방지** - 추측하지 않고, 모르면 "확인 필요" 명시
5. **면책 고지** - 정식 법률 자문은 변호사 상담 필요

---

## 참고 사이트

| 사이트 | URL | 용도 |
|--------|-----|------|
| 국가법령정보센터 | https://law.go.kr | 법령/판례 원문 |
| 열린국회정보 | https://open.assembly.go.kr | 국회 의안 API |
| 대법원 종합법률정보 | https://glaw.scourt.go.kr | 판례 원문 |

---

## 기여하기

버그 리포트, 기능 제안, PR을 환영합니다!

1. Fork
2. Feature branch 생성 (`git checkout -b feat/amazing-feature`)
3. Commit (`git commit -m 'Add amazing feature'`)
4. Push (`git push origin feat/amazing-feature`)
5. Pull Request 생성

---

## 라이선스

MIT License - 자유롭게 사용, 수정, 배포할 수 있습니다.
