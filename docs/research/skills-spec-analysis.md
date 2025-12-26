# Agent Skills 공식 스펙 vs 법순이 구현 분석

> 날짜: 2025-12-23
> 참고: https://agentskills.io

## 1. 공식 스펙 요약

### 1.1 Skills 정의
Agent Skills는 **에이전트가 발견하고 사용할 수 있는 지침, 스크립트, 리소스로 구성된 폴더**.

### 1.2 필수 요소

| 항목 | 요구사항 |
|------|---------|
| **SKILL.md** | 필수 파일 |
| **name** (frontmatter) | 1-64자, 소문자/숫자/하이픈만, 부모 디렉토리명과 일치 |
| **description** (frontmatter) | 1-1024자, 스킬 용도와 트리거 조건 설명 |

### 1.3 선택적 요소

**Frontmatter 필드:**
| 필드 | 설명 |
|------|------|
| `license` | 라이선스 명시 |
| `compatibility` | 환경 요구사항 (1-500자) |
| `metadata` | 커스텀 키-값 쌍 |
| `allowed-tools` | 허용 도구 목록 (실험적) |

**디렉토리 구조:**
```
skill-name/
├── SKILL.md          # 필수
├── scripts/          # 실행 가능한 코드
├── references/       # 추가 문서 (REFERENCE.md, FORMS.md 등)
└── assets/           # 템플릿, 이미지, 데이터
```

### 1.4 권장사항

| 항목 | 권장값 |
|------|-------|
| SKILL.md 크기 | **500줄 미만** |
| 메타데이터 토큰 | ~100 토큰 |
| 지시사항 토큰 | <5000 토큰 |
| Progressive Disclosure | 상세 자료는 별도 파일로 분리 |

---

## 2. 법순이 현재 구현 상황

### 2.1 디렉토리 구조
```
beopsuny/
├── SKILL.md              # 483줄 ✓
├── scripts/              # 7개 Python 스크립트 ✓
├── config/               # 설정 파일들 (스펙에 없음)
│   ├── checklists/       # 7개 체크리스트
│   ├── law_index.yaml
│   ├── legal_terms.yaml
│   └── ...
├── docs/                 # 문서 (references/ 대신)
│   ├── user_guide.md
│   ├── contract_review_guide.md
│   └── international_guide.md
└── data/                 # 캐시/다운로드 (스펙에 없음)
    ├── raw/
    ├── parsed/
    └── bills/
```

### 2.2 SKILL.md Frontmatter

**현재:**
```yaml
---
name: beopsuny
description: 법순이 - 한국 법령/판례 검색, 다운로드, 분석 도우미...
---
```

**분석:**
| 항목 | 스펙 | 현재 | 상태 |
|------|------|------|------|
| name | 1-64자, 소문자/숫자/하이픈 | `beopsuny` (8자) | ✅ 준수 |
| name = 디렉토리명 | 일치해야 함 | 일치 | ✅ 준수 |
| description | 1-1024자 | ~180자 | ✅ 준수 |
| license | 선택 | 없음 | ⚠️ 미설정 |
| compatibility | 선택 | 없음 | ⚠️ 미설정 |
| metadata | 선택 | 없음 | ⚠️ 미설정 |

### 2.3 SKILL.md 크기

| 메트릭 | 권장 | 현재 | 상태 |
|--------|------|------|------|
| 줄 수 | <500 | 483 | ✅ 준수 (하지만 거의 한계) |

---

## 3. 스펙 준수 여부 분석

### 3.1 완전 준수 항목 ✅

1. **SKILL.md 존재**: 필수 파일 있음
2. **name 필드**: 형식 준수, 디렉토리명과 일치
3. **description 필드**: 충분히 설명적
4. **scripts/ 디렉토리**: 스펙 권장 구조 준수
5. **SKILL.md 크기**: 500줄 미만 (483줄)

### 3.2 스펙과 다른 부분 ⚠️

| 항목 | 스펙 | 현재 | 영향도 |
|------|------|------|--------|
| 문서 디렉토리 | `references/` | `docs/` | 낮음 (기능 동일) |
| 설정 디렉토리 | 미정의 | `config/` | 없음 (확장) |
| 데이터 디렉토리 | `assets/` | `data/` | 낮음 (용도 구분) |

### 3.3 미활용 선택 기능 📋

1. **license**: MIT 등 명시 권장
2. **compatibility**: Python 3.9+, BEOPSUNY_OC_CODE 등 명시 가능
3. **metadata**: 버전, 작성자 등 추가 가능
4. **allowed-tools**: Bash, WebSearch 등 명시 가능

---

## 4. 토의 사항

### 4.1 디렉토리 명명 규칙

**질문**: `docs/`를 `references/`로 변경해야 하나?

**고려사항:**
- 스펙은 `references/`를 권장하지만 강제는 아님
- 현재 `docs/`는 일반적인 관례
- 변경 시 기존 문서 참조 경로 수정 필요

**제안**: 현상 유지 또는 점진적 마이그레이션

### 4.2 assets/ vs data/ vs config/

**스펙 정의:**
- `assets/`: 템플릿, 이미지, 데이터 파일

**현재 구조:**
- `config/`: 설정 (settings.yaml, checklists/)
- `data/`: 런타임 캐시 (raw/, parsed/)

**제안**:
- `config/` → 유지 (설정과 리소스 분리는 좋은 패턴)
- `data/` → `.gitignore`에 추가하고 런타임 캐시로 유지
- 정적 assets(템플릿 등)는 별도 `assets/` 생성 검토

### 4.3 선택적 frontmatter 필드 추가

**제안 추가:**
```yaml
---
name: beopsuny
description: 법순이 - 한국 법령/판례 검색...
license: MIT
compatibility: |
  - Python 3.9+
  - 환경변수: BEOPSUNY_OC_CODE (필수)
  - 선택: BEOPSUNY_ASSEMBLY_API_KEY
metadata:
  version: "1.0.0"
  author: "legal-stack"
  language: "ko"
---
```

### 4.4 SKILL.md 크기 관리

**현황**: 483줄 (한계 근접)

**리스크**: 새 기능 추가 시 500줄 초과 가능

**제안**:
1. Quick Reference 섹션을 `references/quick-reference.md`로 분리
2. 체크리스트 관련 내용을 `references/checklists.md`로 분리
3. SKILL.md는 핵심 워크플로우에 집중

---

## 5. SKILL.md 일관성 분석

### 5.1 현재 섹션 구조

```
## 핵심 원칙 (10줄)
## 필수 명령어 (20줄)
## 검색 대상 코드 (35줄)
## 기능별 명령어 (48줄)           ← 하위 섹션 10개
## Claude 실행 워크플로우 (147줄)  ← ⭐ IMPORTANT
## 정부 집행 스탠스 파악 (203줄)   ← ⭐ IMPORTANT
## API 설정 (226줄)
## 계약서 검토 보조 (246줄)
## 해외 진출 시 확인 가이드 (316줄)
## 외부 참고 사이트 (341줄)
## 법순이 범위 외 업무 (371줄)
## Instructions for Claude (384줄)  ← 핵심 원칙과 중복
## Quick Reference (411줄)          ← 위 내용 요약 (중복)
```

### 5.2 일관성 문제

| 문제 | 설명 | 영향 |
|------|------|------|
| **내용 중복** | "핵심 원칙" ↔ "Instructions for Claude" | 유지보수 시 동기화 필요 |
| **요약 중복** | "필수 명령어" ↔ "Quick Reference" | 어디를 봐야 할지 혼란 |
| **논리적 순서** | API 설정이 중간에 위치 | 설정은 보통 끝이나 시작 |
| **섹션 역할 불명확** | "기능별 명령어" vs "Quick Reference" | 둘 다 명령어 목록 |

### 5.3 구조 개선안

**Option A: 역할 기반 재구성**
```
1. Overview (핵심 원칙 + 범위)
2. Setup (API 설정, 환경)
3. Core Workflows (Claude 실행 워크플로우)
4. Commands Reference (통합된 명령어 목록)
5. Use Cases (계약서, 해외진출 등)
6. External Resources (외부 사이트)
```

**Option B: 최소 변경 (중복 제거만)**
```
- "Instructions for Claude" → "핵심 원칙"으로 통합
- "Quick Reference" → references/로 분리
- API 설정 → 문서 상단 또는 하단으로 이동
```

### 5.4 Progressive Disclosure 적용안

| 유지 (SKILL.md) | 분리 (references/) |
|-----------------|-------------------|
| 핵심 원칙 | Quick Reference |
| Claude 실행 워크플로우 | 체크리스트 상세 |
| 필수 명령어 (축약) | 전체 명령어 레퍼런스 |
| 정부 집행 스탠스 | 외부 참고 사이트 상세 |

---

## 6. 한글/영어 혼용 분석

### 6.1 현재 상태

| 요소 | 현재 언어 | 예시 |
|------|----------|------|
| 제목 | 한글 + (영어) | "Quick Reference (빠른 참조)" |
| 명령어 설명 | 한글 | "정확한 법령 검색" |
| 코드/CLI | 영어 | `fetch_law.py exact "상법"` |
| 표 헤더 | 한글 | "용도", "명령어" |
| 메모/경고 | 한글 | "⭐ IMPORTANT" |

### 6.2 한글 유지 장점

1. **도메인 특성**: 한국법 업무 → 한국어가 자연스러움
2. **사용자 친화**: 한국인 사용자 대상
3. **법률 용어**: 한글 법령명이 검색에 그대로 사용됨
4. **일관성**: 현재 전체가 한글로 통일

### 6.3 영어 혼용 고려사항

**영어가 나을 수 있는 부분:**
| 요소 | 현재 | 대안 | 이유 |
|------|------|------|------|
| 섹션 제목 | "빠른 참조" | "Quick Reference" | 국제 표준 용어 |
| 표 헤더 | "용도", "명령어" | "Purpose", "Command" | 코드와 일관성 |
| 메타 키워드 | "⭐ 중요" | "⭐ IMPORTANT" | 이미 혼용 중 |

**한글 유지가 나은 부분:**
| 요소 | 예시 | 이유 |
|------|------|------|
| 법령명 | "개인정보보호법" | 검색어로 사용 |
| 워크플로우 설명 | "법령 조문 확인" | 도메인 맥락 |
| 경고/면책 | "변호사 상담 필요" | 법적 뉘앙스 |

### 6.4 제안: 하이브리드 접근

```markdown
# 핵심 섹션 제목
## Core Principles (핵심 원칙)     ← 영어 주, 한글 부
## Commands Reference             ← 영어
## 법률 조사 워크플로우            ← 한글 (도메인)

# 표 헤더
| Command | 용도 | 예시 |         ← 하이브리드

# 본문
- 법령 검색: `fetch_law.py exact "민법"`  ← 한글 설명 + 영어 코드
```

**결정 기준:**
- 에이전트가 파싱/매칭하는 부분 → 영어 권장
- 사용자가 읽는 설명 → 한글 유지
- 법률 용어 → 한글 필수

---

## 7. 권장 개선 사항 (우선순위순)

### P1: 필수/권장 준수

| # | 작업 | 이유 |
|---|------|------|
| 1 | frontmatter에 `license` 추가 | 배포 시 라이선스 명확화 |
| 2 | frontmatter에 `compatibility` 추가 | 사용자가 환경 요구사항 파악 |

### P2: 구조 개선

| # | 작업 | 이유 |
|---|------|------|
| 3 | SKILL.md에서 Quick Reference 분리 | 500줄 한도 여유 확보 |
| 4 | `docs/` → `references/` 마이그레이션 검토 | 스펙 일관성 (선택적) |

### P3: 메타데이터 강화

| # | 작업 | 이유 |
|---|------|------|
| 5 | `metadata` 필드에 버전/작성자 추가 | 관리 용이성 |
| 6 | `allowed-tools` 명시 (실험적) | 보안/투명성 |

### P4: 일관성 개선

| # | 작업 | 이유 |
|---|------|------|
| 7 | "Instructions for Claude" → "핵심 원칙" 통합 | 중복 제거 |
| 8 | 섹션 순서 재배치 (API 설정 위치) | 논리적 흐름 |
| 9 | 한글/영어 하이브리드 규칙 정립 | 일관된 스타일 |

---

## 8. 결론

**법순이 스킬은 Agent Skills 공식 스펙을 대체로 잘 준수**하고 있습니다.

### 강점
- 필수 요소(SKILL.md, name, description) 완벽 준수
- scripts/ 디렉토리 구조 준수
- SKILL.md 크기 권장사항 내 (483줄)
- 한국법 도메인에 특화된 풍부한 콘텐츠

### 개선 기회

| 영역 | 현재 | 개선 방향 |
|------|------|----------|
| **Frontmatter** | name, description만 | license, compatibility, metadata 추가 |
| **디렉토리** | docs/, data/ | references/, assets/ 스펙 정렬 검토 |
| **구조** | 13개 섹션, 일부 중복 | 역할별 재구성, 중복 제거 |
| **언어** | 100% 한글 | 하이브리드 규칙 정립 검토 |

### 다음 단계 제안

**Phase 1: 메타데이터 (즉시 적용 가능)**
- frontmatter에 license, compatibility 추가

**Phase 2: 구조 최적화 (중기)**
- Quick Reference → references/로 분리
- 중복 섹션 통합 (핵심 원칙 ↔ Instructions for Claude)

**Phase 3: 전체 리팩토링 (장기)**
- 역할 기반 섹션 재구성
- 한글/영어 하이브리드 규칙 적용
- docs/ → references/ 마이그레이션

**호환성 평가: 높음** - 현재 상태로도 스펙 호환 에이전트에서 정상 작동 예상

---

## 9. 결정 사항 (2025-12-23)

| 항목 | 결정 | 비고 |
|------|------|------|
| **디렉토리** | `docs/` → `references/` 변경 | 스펙 정렬 |
| **언어** | 한글 주도 + 영어 하이브리드 | 세계 표준 부분만 영어 |
| **구조 개편** | Option A (전면 재구성) | 역할 기반 구조 |
| **config/** | 스펙 정렬 (정적 데이터 분리) | 아래 최종 결정 참조 |
| **ZIP 배포** | 현행 GitHub Actions 유지 | Anthropic 대안 제공 시까지 |

### config/ 최종 결정 (2025-12-23 추가)

**방향**: 스펙 정렬 + 역할별 분리

**변경 계획:**
1. `settings.yaml`에서 중복 데이터 제거 (secrets만 유지)
2. 정적 데이터 → `assets/` 이동 (스펙 정의)
3. 문서 → `references/` 이동 (스펙 정의)

**최종 디렉토리 구조:**
```
beopsuny/
├── SKILL.md                    # 재구성 (Option A)
├── scripts/                    # 유지
├── config/                     # secrets + 런타임 설정만
│   ├── settings.yaml           # secrets only (.gitignore)
│   └── settings.yaml.example   # 템플릿
├── assets/                     # 정적 데이터 (신규)
│   ├── law_index.yaml
│   ├── legal_terms.yaml
│   ├── clause_references.yaml
│   ├── forms.yaml
│   └── checklists/
├── references/                 # 문서 (docs/ → 변경)
│   ├── quick-reference.md      # SKILL.md에서 분리
│   ├── external-sites.md       # SKILL.md에서 분리
│   ├── user_guide.md
│   ├── contract_review_guide.md
│   └── international_guide.md
└── data/                       # 런타임 캐시 (유지)
    ├── raw/
    ├── parsed/
    └── bills/
```

**ZIP 배포 (현행 유지):**
- GitHub Actions에서 secrets 주입
- Anthropic이 환경변수 UI 제공 시까지 현행 방식 유지

### 한글/영어 하이브리드 규칙 (확정)

| 요소 | 언어 | 예시 |
|------|------|------|
| **섹션 제목** | 영어 (+ 한글 부제) | `## Setup (환경 설정)` |
| **표 헤더 (기술)** | 영어 | Command, Type, Output |
| **법령명/법률용어** | 한글 | "개인정보보호법", "과징금" |
| **워크플로우 설명** | 한글 | "법령 조문 확인 후..." |
| **코드/CLI** | 영어 | `fetch_law.py exact` |
| **경고/면책** | 한글 | "변호사 상담 필요" |

### 구조 재구성 계획 (Option A)

**새로운 SKILL.md 구조:**
```
---
(frontmatter with license, compatibility, metadata)
---

# Beopsuny (법순이)

## 1. Overview (개요)
   - 핵심 원칙 5가지
   - 스킬 범위 및 제한사항

## 2. Setup (환경 설정)
   - API 설정 (환경변수)
   - 게이트웨이 설정 (해외)

## 3. Core Workflows (핵심 워크플로우)
   - 법률 조사 9단계 워크플로우 ⭐
   - 정부 집행 스탠스 파악 ⭐
   - WebSearch 템플릿

## 4. Commands Reference (명령어)
   - 법령 검색/다운로드
   - 판례 검색
   - 국회 의안
   - 체크리스트

## 5. Use Cases (활용 사례)
   - 계약서 검토 보조
   - 해외 진출 시 확인
   - 주간 규제 점검

## 6. Resources (참고 자료)
   → references/ 로 분리
```

**분리할 파일 (references/):**
| 파일 | 내용 |
|------|------|
| `quick-reference.md` | 자주 쓰는 명령어 치트시트 |
| `external-sites.md` | 외부 참고 사이트 목록 |
| `checklists.md` | 체크리스트 사용 가이드 |

---

## 10. 열린 토론: config/ 및 API Key 관리

### 10.1 현재 구현

```
beopsuny/
└── config/
    ├── settings.yaml      ← API key 포함 가능
    └── settings.yaml.example
```

**사용 방식:**
1. 환경변수: `BEOPSUNY_OC_CODE` (표준)
2. config 파일: `settings.yaml` (Claude Code App zip 배포용)

### 10.2 문제점

| 이슈 | 설명 |
|------|------|
| **보안** | API key가 zip에 포함될 수 있음 |
| **표준과 거리** | 스펙에서는 환경변수/시스템 설정 권장 |
| **배포 복잡성** | 사용자별로 다른 key 필요 |

### 10.3 웹검색 조사 결과 (2025-12-23)

#### 업계 현황: "Minefield"

> "Configuring MCP often feels like a minefield, especially when secrets like API keys and database passwords are involved."
> — [MCP configuration is a sh*tsh*w](https://0xhagen.medium.com/mcp-configuration-is-a-sh-tshow-but-heres-how-i-fixed-secrets-handling-5395010762a1)

**핵심 문제:**
- 일부 서버는 환경변수 지원, 일부는 config에 하드코딩 강제
- 팀 공유 시 각자 다른 credentials 필요
- 표준화된 방식 부재

#### 권장 패턴들

**1. 환경변수 우선 (표준)**
```
환경변수 > CLI 플래그 > config 파일 > 기본값
```

- [Anthropic 권장](https://support.claude.com/en/articles/9767949-api-key-best-practices-keeping-your-keys-safe-and-secure): 환경변수로 secrets 주입
- [MCP Best Practices](https://www.stainless.com/mcp/mcp-server-configuration-best-practices): `${API_TOKEN}` 형식으로 환경변수 참조
- Config 파일에 credentials 직접 저장 지양

**2. Prefix 패턴 (SkillPort 예시)**

[SkillPort](https://github.com/gotalab/skillport)는 `SKILLPORT_` prefix로 모든 설정 관리:
```bash
SKILLPORT_SKILLS_DIR=/path/to/skills
SKILLPORT_LOG_LEVEL=info
SKILLPORT_EMBEDDING_PROVIDER=openai
```

**GitHub 인증 fallback chain:**
1. `GH_TOKEN` 환경변수
2. `GITHUB_TOKEN` 환경변수
3. `gh auth token` (CLI 자동 감지)

**3. Secrets Manager 연동**

[Keeper Security MCP](https://docs.keeper.io/en/keeperpam/secrets-manager/integrations/model-context-protocol-mcp-for-ai-agents-node):
- Zero-Trust: AI 에이전트는 지정된 폴더에만 접근
- Human-in-the-Loop: 민감한 작업 시 사용자 확인
- Cross-Platform: Linux, macOS, Windows, Docker

[Doppler AI Agents](https://relevanceai.com/agent-templates-software/doppler):
- 코드베이스 스캔으로 secrets 탐지
- 보안 저장소로 자동 이동

**4. 설정 파일 scope 활용**

[VS Code MCP](https://code.visualstudio.com/docs/copilot/customization/mcp-servers):
- 프로젝트별: `.vscode/mcp.json` (팀 공유용, secrets 제외)
- 사용자별: `~/.config/` (개인 credentials)
- 더 specific한 scope가 우선

#### 팀 공유 문제

> "We don't want environment variables in git, so having a custom script for each MCP server which exports these ENV vars feels like a solution that isn't really scalable for a team."
> — [Cursor Forum](https://forum.cursor.com/t/resolve-local-environment-variables-in-mcp-server-definitions/79639)

**해결 패턴:**
| 방식 | 장점 | 단점 |
|------|------|------|
| `.env` + `.env.example` | 간단 | 각자 수동 설정 |
| Secrets Manager | 중앙 관리 | 인프라 필요 |
| CLI 인증 (gh auth) | 일회성 설정 | 도구 의존 |

### 10.4 법순이 적용 방안

#### 현재 (Dual Mode)
```python
# 1순위: 환경변수
oc_code = os.getenv('BEOPSUNY_OC_CODE')
# 2순위: config 파일 (fallback)
if not oc_code:
    oc_code = load_from_yaml('config/settings.yaml')
```

#### Option A: 환경변수 Only (표준 정렬)

**변경:**
- `settings.yaml`에서 API key 필드 제거
- `settings.yaml.example`에 환경변수 설정 가이드
- SKILL.md에 환경변수 설정 명확히 문서화

**장점:**
- 스펙/업계 표준과 일치
- zip 배포 시 credentials 누출 방지
- 팀 공유 용이

**단점:**
- Claude Code App zip 배포 시 불편
- 사용자가 환경변수 설정해야 함

#### Option B: Prefix 패턴 도입

**변경:**
```bash
# 모든 설정을 BEOPSUNY_ prefix로 통일
BEOPSUNY_OC_CODE=xxx
BEOPSUNY_ASSEMBLY_API_KEY=xxx
BEOPSUNY_GATEWAY_URL=xxx
BEOPSUNY_LOG_LEVEL=info
```

**장점:**
- 네임스페이스 충돌 방지
- 설정 관리 용이

#### Option C: 하이브리드 (현행 개선)

**변경:**
- `settings.yaml`: API key 외 설정만 (log level, timeout 등)
- API key: 환경변수 only
- `.gitignore`에 `settings.yaml` 추가 (선택적)

**장점:**
- 기존 사용자 호환
- 보안 개선

### 10.5 Claude Code App zip 배포 문제

**문제:**
- zip에 API key 포함 시 보안 위험
- 환경변수만 사용하면 zip 배포 후 추가 설정 필요

**잠재적 해결책:**
1. **설치 후 설정 스크립트**: `setup.sh`로 환경변수 설정 안내
2. **최초 실행 시 프롬프트**: API key 없으면 사용자에게 요청
3. **Keychain/Credential Manager 연동**: 시스템 보안 저장소 활용

### 10.6 결론 및 권장

| 시나리오 | 권장 방식 |
|---------|----------|
| **개인 사용** | 환경변수 (현행) |
| **팀 공유** | `.env.example` + 각자 `.env` |
| **zip 배포** | 설치 후 안내 + 환경변수 설정 |
| **엔터프라이즈** | Secrets Manager 연동 (장기) |

**단기 조치:**
1. `settings.yaml`에서 API key 관련 필드 제거 검토
2. SKILL.md의 Setup 섹션에 환경변수 설정 명확히 문서화
3. `BEOPSUNY_` prefix 패턴 정식 채택

**장기 고려:**
- Secrets Manager MCP 연동 (Keeper, Doppler 등)
- Claude Code App의 secrets 관리 기능 개선 대기

### 10.7 config/ 디렉토리 상세 분석 (2025-12-23)

#### 현재 파일 구조 및 크기

```
config/                              총 6,269줄
├── settings.yaml           60줄   ← secrets + 설정 혼재
├── settings.yaml.example   45줄   ← 템플릿
├── law_index.yaml         328줄   ← 법령/행정규칙 ID
├── legal_terms.yaml     1,908줄   ← 영한 법률용어 사전 (99개)
├── clause_references.yaml 946줄   ← 계약조항-법령 매핑
├── forms.yaml             136줄   ← 양식 링크
└── checklists/          2,891줄   ← 7개 체크리스트
    ├── startup.yaml       303줄
    ├── privacy_compliance 357줄
    ├── fair_trade.yaml    320줄
    ├── contract_review    495줄
    ├── labor_hr.yaml      486줄
    ├── serious_accident   385줄
    ├── investment_dd      545줄
    └── MAINTENANCE.md
```

#### 파일별 역할 분류

| 파일 | 유형 | Secrets 포함 | Git 추적 |
|------|------|-------------|---------|
| `settings.yaml` | 런타임 설정 | ✅ API keys | ❌ (.gitignore) |
| `settings.yaml.example` | 템플릿 | ❌ | ✅ |
| `law_index.yaml` | 정적 데이터 | ❌ | ✅ |
| `legal_terms.yaml` | 정적 데이터 | ❌ | ✅ |
| `clause_references.yaml` | 정적 데이터 | ❌ | ✅ |
| `forms.yaml` | 정적 데이터 | ❌ | ✅ |
| `checklists/*.yaml` | 정적 데이터 | ❌ | ✅ |

#### settings.yaml 현재 내용 (문제점)

```yaml
# 실제 파일 내용 (secrets + 설정 + 데이터 혼재)
oc_code: "xxx"              # ← secrets
assembly_api_key: "xxx"      # ← secrets
gateway:
  url: "xxx"                 # ← secrets
  api_key: "xxx"             # ← secrets
api:
  base_url: "..."            # ← 설정 (변경 거의 없음)
  timeout: 30                # ← 설정
targets:                     # ← 정적 데이터 (law_index.yaml과 중복)
  law: "법령"
major_laws:                  # ← 정적 데이터 (law_index.yaml과 완전 중복!)
  민법: "001706"
```

**문제점:**
1. secrets와 설정이 한 파일에 혼재
2. `major_laws`가 `law_index.yaml`과 중복
3. `targets`는 변경될 일 없는 상수

#### 제안: 역할별 분리

**Option 1: 현행 구조 개선**
```
config/
├── settings.yaml           # secrets only (환경변수 fallback)
│   └── oc_code, api_key, gateway만
├── settings.yaml.example   # 템플릿
├── law_index.yaml          # 법령 ID (중복 제거)
├── legal_terms.yaml        # 용어 사전
├── clause_references.yaml  # 조항 매핑
├── forms.yaml              # 양식 링크
└── checklists/             # 체크리스트
```

**Option 2: 스펙 정렬 (references/ 활용)**
```
beopsuny/
├── config/                 # secrets + 런타임 설정만
│   ├── settings.yaml       # secrets only
│   └── settings.yaml.example
├── references/             # 정적 데이터 (스펙 권장)
│   ├── law_index.yaml
│   ├── legal_terms.yaml
│   ├── clause_references.yaml
│   ├── forms.yaml
│   └── checklists/
└── scripts/
```

**Option 3: assets/ 활용 (스펙 정렬)**
```
beopsuny/
├── config/                 # secrets만
├── assets/                 # 정적 데이터 (스펙 정의)
│   ├── data/
│   │   ├── law_index.yaml
│   │   └── legal_terms.yaml
│   └── checklists/
└── references/             # 문서 (docs/ 대체)
```

#### 현재 방식의 장단점

**장점:**
- 단순: 모든 설정이 한 곳
- 스크립트에서 config/ 경로만 참조

**단점:**
- secrets와 정적 데이터 혼재
- 스펙 표준과 불일치
- 6,000줄+ 데이터가 config에 존재

#### ZIP 배포 관점에서 분석

**GitHub Actions 워크플로우 (현재):**
```yaml
# 1. settings.yaml.example → settings.yaml 생성
# 2. API keys 주입
# 3. 전체 config/ 포함하여 ZIP
```

**문제:**
- 정적 데이터(law_index 등)도 매번 ZIP에 포함
- 버전 관리 어려움

**개선안:**
- secrets만 별도 주입
- 정적 데이터는 기본 포함 (변경 없음)

#### 권장 사항

**단기 (현행 개선):**
1. `settings.yaml`에서 `major_laws`, `targets` 제거 (law_index.yaml로 통합)
2. secrets 필드만 유지: `oc_code`, `assembly_api_key`, `gateway`

**중기 (스펙 정렬):**
1. 정적 데이터 → `references/` 또는 `assets/` 이동
2. `config/` → secrets + 런타임 설정만

**ZIP 배포 개선:**
1. `settings.yaml` 템플릿만 포함
2. 설치 후 환경변수 또는 설정 안내
3. (현실적) 개인용은 현행 유지, 공개용은 템플릿만

---

### 10.8 Claude.ai 웹앱 Skills 환경변수 조사 (2025-12-23)

#### 현재 상황: 환경변수 설정 UI 없음

**조사 결과:**
| 항목 | 상태 |
|------|------|
| Claude.ai Skills 환경변수 설정 UI | ❌ **없음** |
| ZIP 업로드 외 설치 방법 | ❌ 없음 |
| API key 설정 후처리 방법 | ❌ 명시 안됨 |

**공식 문서 언급:**
> "민감한 정보(API 키, 비밀번호)를 하드코딩하지 마세요"
> "외부 서비스 접근을 위해 적절한 **MCP 연결**을 사용하세요"
> — [Creating Custom Skills](https://support.claude.com/en/articles/12512198-creating-custom-skills)

**문제점:**
- "하드코딩하지 말라"고 하면서 대안 UI를 제공하지 않음
- MCP 연결 사용하라고 하지만, Claude.ai 웹앱에서 MCP 설정은 별도 영역
- ZIP 배포 시 secrets 포함 외에는 현실적 방법이 없음

#### Claude.ai vs Claude Code 비교

| 기능 | Claude.ai (웹앱) | Claude Code (CLI) |
|------|-----------------|-------------------|
| Skills 설치 | ZIP 업로드만 | `~/.claude/skills/` 폴더 |
| 환경변수 설정 | ❌ UI 없음 | ✅ `.bashrc`, `settings.json` |
| Secrets 관리 | ❌ 방법 없음 | ✅ 환경변수, deny 설정 |
| MCP 연결 | 별도 설정 | `mcp.json` 통합 |

#### 향후 개선 계획 (Anthropic 발표)

[Anthropic 공식 블로그](https://www.anthropic.com/news/skills)에서 언급된 로드맵:

> "We're working toward **simplified skill creation workflows** and **enterprise-wide deployment capabilities**, making it easier for organizations to distribute skills across teams."

**언급된 기능:**
- ✅ 중앙 관리자 설정 (Team/Enterprise)
- ✅ Skills 프로비저닝 제어
- ✅ 사용 패턴 모니터링

**언급 안 된 기능:**
- ❌ 사용자별 환경변수/secrets 설정 UI
- ❌ ZIP 배포 외 설치 방법
- ❌ Secrets Manager 연동

#### 결론: 현재 workaround가 유일한 방법

**사용자 상황 (GitHub Actions로 key 주입 후 ZIP 생성):**
```
1. settings.yaml.example 작성
2. GitHub Actions에서 환경변수로 API key 주입
3. settings.yaml 생성 후 ZIP 패키징
4. 개인용 ZIP으로 배포
```

**이 방식의 평가:**
| 장점 | 단점 |
|------|------|
| 현재 유일한 작동 방법 | 보안상 이상적이지 않음 |
| 자동화 가능 | ZIP에 secrets 포함 |
| 받는 사람은 설정 불필요 | 공개 배포 불가 |

**개선 희망 사항 (Anthropic에 피드백 필요):**
1. Claude.ai Skills에 환경변수 설정 UI 추가
2. 설치 후 configuration step 지원
3. 시스템 Keychain/Credential Manager 연동
4. MCP secrets와 Skills 통합

### 10.8 참고 자료

- [API Key Best Practices - Claude Help Center](https://support.claude.com/en/articles/9767949-api-key-best-practices-keeping-your-keys-safe-and-secure)
- [MCP Server Configuration Best Practices - Stainless](https://www.stainless.com/mcp/mcp-server-configuration-best-practices)
- [SkillPort Configuration Guide](https://github.com/gotalab/skillport/blob/main/guide/configuration.md)
- [Keeper MCP Integration](https://docs.keeper.io/en/keeperpam/secrets-manager/integrations/model-context-protocol-mcp-for-ai-agents-node)
- [MCP configuration secrets handling](https://0xhagen.medium.com/mcp-configuration-is-a-sh-tshow-but-heres-how-i-fixed-secrets-handling-5395010762a1)
- [Introducing Agent Skills - Anthropic](https://www.anthropic.com/news/skills)
- [Creating Custom Skills](https://support.claude.com/en/articles/12512198-creating-custom-skills)

---

## 11. 구현 계획

### Phase 1: 디렉토리 구조 변경

**작업 목록:**
| # | 작업 | 파일/디렉토리 |
|---|------|--------------|
| 1.1 | `docs/` → `references/` 이름 변경 | 디렉토리 |
| 1.2 | `assets/` 디렉토리 생성 | 신규 |
| 1.3 | 정적 데이터 이동 | config/ → assets/ |
| 1.4 | `settings.yaml` 정리 | secrets만 유지 |

**상세:**
```bash
# 1.1 docs → references
mv docs references

# 1.2 assets 생성
mkdir assets

# 1.3 정적 데이터 이동
mv config/law_index.yaml assets/
mv config/legal_terms.yaml assets/
mv config/clause_references.yaml assets/
mv config/forms.yaml assets/
mv config/checklists assets/

# 1.4 settings.yaml에서 중복 제거
# - major_laws 삭제 (law_index.yaml로 통합)
# - targets 삭제 (스크립트에 하드코딩 또는 별도 상수 파일)
```

### Phase 2: 스크립트 경로 업데이트

**영향받는 스크립트:**
| 스크립트 | 변경 내용 |
|---------|----------|
| `fetch_law.py` | config/ → assets/ 경로 |
| 기타 스크립트 | 동일 |

**변경 패턴:**
```python
# Before
CONFIG_DIR = Path(__file__).parent.parent / "config"
# After
ASSETS_DIR = Path(__file__).parent.parent / "assets"
CONFIG_DIR = Path(__file__).parent.parent / "config"  # secrets only
```

### Phase 3: SKILL.md 재구성 (Option A)

**새로운 구조:**
```markdown
---
name: beopsuny
description: ...
license: MIT
compatibility: |
  - Python 3.9+
  - BEOPSUNY_OC_CODE 환경변수 필수
metadata:
  version: "2.0.0"
  language: "ko"
---

# Beopsuny (법순이)

## 1. Overview (개요)
## 2. Setup (환경 설정)
## 3. Core Workflows (핵심 워크플로우)
## 4. Commands Reference (명령어)
## 5. Use Cases (활용 사례)
## 6. Resources (참고 자료) → references/ 링크
```

**분리할 내용:**
| 현재 섹션 | 이동 위치 |
|----------|----------|
| Quick Reference | `references/quick-reference.md` |
| 외부 참고 사이트 | `references/external-sites.md` |
| Instructions for Claude | Overview로 통합 |

### Phase 4: 한글/영어 하이브리드 적용

**적용 규칙:**
- 섹션 제목: `## Setup (환경 설정)`
- 표 헤더 (기술): Command, Type, Output
- 법령명/용어: 한글 유지
- 코드/CLI: 영어

### Phase 5: Frontmatter 확장

**추가할 필드:**
```yaml
---
name: beopsuny
description: 법순이 - 한국 법령/판례 검색...
license: MIT
compatibility: |
  - Python 3.9+
  - 환경변수: BEOPSUNY_OC_CODE (필수)
  - 선택: BEOPSUNY_ASSEMBLY_API_KEY, BEOPSUNY_GATEWAY_URL
metadata:
  version: "2.0.0"
  author: "legal-stack"
  language: "ko"
  repository: "https://github.com/..."
---
```

### 작업 순서 (권장)

```
1. Phase 1: 디렉토리 구조 변경
   ↓
2. Phase 2: 스크립트 경로 업데이트
   ↓
3. 테스트: 기존 기능 동작 확인
   ↓
4. Phase 3: SKILL.md 재구성
   ↓
5. Phase 4: 한글/영어 하이브리드 적용
   ↓
6. Phase 5: Frontmatter 확장
   ↓
7. GitHub Actions 워크플로우 경로 업데이트
```

### 예상 영향

| 영역 | 영향 | 대응 |
|------|------|------|
| 기존 스크립트 | 경로 변경 | 경로 상수 업데이트 |
| SKILL.md 참조 | 경로 변경 | 새 경로로 업데이트 |
| GitHub Actions | 경로 변경 | 워크플로우 수정 |
| 사용자 | 거의 없음 | 환경변수 방식 동일 |

---

---

## 12. 최종 리뷰 (2025-12-25)

### 12.1 웹검색 검증 결과

#### ✅ 디렉토리 구조 결정 검증

**공식 스펙 및 베스트 프랙티스 확인:**

| 디렉토리 | 스펙 정의 | 우리 결정 | 검증 결과 |
|---------|----------|----------|----------|
| `references/` | 문서, 컨텍스트에 로드됨 | `docs/` → `references/` 변경 | ✅ 스펙 일치 |
| `assets/` | 템플릿, 바이너리 파일 | 정적 데이터 이동 | ✅ 스펙 일치 |
| `scripts/` | 실행 가능한 코드 | 현행 유지 | ✅ 이미 준수 |
| `config/` | 스펙 미정의 | secrets만 유지 | ⚠️ 확장 (허용됨) |

**참고**: [Agent Skills Specification](https://agentskills.io/specification) 및 [Deep Dive 분석](https://leehanchung.github.io/blogs/2025/10/26/claude-skills-deep-dive/)

#### ✅ Progressive Disclosure 패턴 검증

**핵심 원칙 확인됨:**
> "Progressive disclosure is the core design principle that makes Agent Skills flexible and scalable."
> — [Anthropic Engineering Blog](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)

**3단계 로딩 모델:**
1. **Metadata** (~100 tokens): 스킬 이름/설명만 로드
2. **Instructions** (<5k tokens): SKILL.md 본문 로드
3. **Resources**: 필요 시 scripts/references/assets에서 동적 로드

**우리 적용:**
- SKILL.md 483줄 → Quick Reference 분리로 여유 확보 ✅
- 세부 내용 references/로 분리 ✅

#### ✅ SKILL.md 500줄 규칙 검증

**공식 베스트 프랙티스:**
> "Keep SKILL.md body under 500 lines for optimal performance. If your content exceeds this, split it into separate files."
> — [Skill authoring best practices](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices)

**현재 상태**: 483줄 (한계 근접)
**개선 계획**: Quick Reference, 외부 사이트 분리 → 예상 350줄 이하 ✅

#### ✅ skills-ref validate 도구 확인

**CLI 도구 존재 확인:**
```bash
pip install skills-ref
skills-ref validate path/to/skill
```

**활용 방안:**
- CI에 통합하여 스킬 유효성 자동 검증
- GitHub Actions 워크플로우에 추가 권장

**참고**: [skills-ref GitHub](https://github.com/agentskills/agentskills/tree/main/skills-ref)

### 12.2 리뷰 의견

#### 👍 잘 결정된 사항

| # | 결정 | 이유 |
|---|------|------|
| 1 | `docs/` → `references/` | 스펙 권장 구조와 일치 |
| 2 | 정적 데이터 → `assets/` | 역할별 분리 명확, 스펙 정의와 일치 |
| 3 | SKILL.md Option A 재구성 | 역할 기반 구조가 Progressive Disclosure에 적합 |
| 4 | 한글/영어 하이브리드 | 도메인(법률)은 한글, 기술 용어는 영어로 실용적 |
| 5 | ZIP 배포 현행 유지 | Anthropic 대안 부재, 현실적 선택 |

#### 🔍 추가 고려사항

**1. skills-ref validate CI 통합**

현재 구현 계획에 없으나 추가 권장:
```yaml
# .github/workflows/validate-skill.yml
- name: Validate Skill
  run: |
    pip install skills-ref
    skills-ref validate .claude/skills/beopsuny
```

**2. assets/ 하위 구조**

현재 계획:
```
assets/
├── law_index.yaml
├── legal_terms.yaml
├── ...
└── checklists/
```

권장 개선 (선택적):
```
assets/
├── data/           # 정적 데이터
│   ├── law_index.yaml
│   └── legal_terms.yaml
├── templates/      # 템플릿 (향후)
└── checklists/     # 체크리스트
```

**이유**: 스펙에서 assets/는 "templates and binary files"로 정의, 데이터와 템플릿 구분 시 확장성 증가

**3. Frontmatter metadata 버전 관리**

제안에 `version: "2.0.0"` 포함되어 있으나, semantic versioning 정책 명시 필요:
- Major: 구조 변경 (breaking)
- Minor: 기능 추가
- Patch: 버그 수정, 데이터 업데이트

**4. 참고 자료 섹션 업데이트**

현재 참고 자료가 agentskills.io 4개 링크만 있음. 검증 과정에서 발견한 유용한 자료 추가 권장.

### 12.3 보완이 필요한 영역

| # | 영역 | 현재 상태 | 권장 |
|---|------|----------|------|
| 1 | CI 검증 | 없음 | skills-ref validate 추가 |
| 2 | 버전 정책 | 미정의 | CHANGELOG + SemVer |
| 3 | 테스트 | 언급만 | 스크립트 단위 테스트 계획 |
| 4 | 마이그레이션 가이드 | 없음 | 기존 사용자용 가이드 필요 |

### 12.4 구현 우선순위 재확인

**Phase 1 (즉시):**
1. 디렉토리 구조 변경 (docs/ → references/, assets/ 생성)
2. config/ 정리 (secrets만 유지)
3. 스크립트 경로 업데이트
4. **추가**: skills-ref validate로 검증

**Phase 2 (중기):**
1. SKILL.md 재구성 (Option A)
2. Frontmatter 확장 (license, compatibility, metadata)
3. 한글/영어 하이브리드 적용
4. **추가**: CI 워크플로우에 validate 통합

**Phase 3 (장기):**
1. 테스트 코드 추가
2. 마이그레이션 가이드 작성
3. 버전 관리 정책 수립

### 12.5 결론

토의 문서의 결정사항들은 **Agent Skills 공식 스펙 및 베스트 프랙티스와 잘 정렬**되어 있습니다.

**강점:**
- 스펙 표준 디렉토리 구조 채택 (references/, assets/)
- Progressive Disclosure 원칙 적용
- 500줄 규칙 준수 계획
- 현실적인 배포 전략 (ZIP + GitHub Actions)

**보완 권장:**
- skills-ref validate CI 통합
- assets/ 하위 구조 세분화 검토
- 버전 관리 정책 명시

**구현 준비 완료**: 이 문서를 기반으로 에픽/이슈 도출 진행 가능

---

## 참고 자료

### 공식 스펙
- [Agent Skills Home](https://agentskills.io/home)
- [What are Skills](https://agentskills.io/what-are-skills)
- [Specification](https://agentskills.io/specification)
- [Integrate Skills](https://agentskills.io/integrate-skills)

### 베스트 프랙티스
- [Skill authoring best practices - Claude Docs](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices)
- [Equipping agents for the real world - Anthropic Engineering](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [Claude Agent Skills: A First Principles Deep Dive](https://leehanchung.github.io/blogs/2025/10/26/claude-skills-deep-dive/)

### 도구 및 구현
- [skills-ref - GitHub](https://github.com/agentskills/agentskills/tree/main/skills-ref)
- [Agent Skills - Claude Code Docs](https://code.claude.com/docs/en/skills)
- [SkillPort](https://github.com/gotalab/skillport)

### Secrets 관리
- [API Key Best Practices - Claude Help Center](https://support.claude.com/en/articles/9767949-api-key-best-practices-keeping-your-keys-safe-and-secure)
- [MCP Server Configuration Best Practices](https://www.stainless.com/mcp/mcp-server-configuration-best-practices)
- [MCP configuration secrets handling](https://0xhagen.medium.com/mcp-configuration-is-a-sh-tshow-but-heres-how-i-fixed-secrets-handling-5395010762a1)
