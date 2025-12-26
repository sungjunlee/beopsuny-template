# Agent Skills 스펙 정렬 구현 에픽/이슈

> 참조: [skills-spec-analysis.md](./skills-spec-analysis.md)
> 생성일: 2025-12-25

---

## Epic 1: 디렉토리 구조 스펙 정렬

**목표**: Agent Skills 공식 스펙에 맞춰 디렉토리 구조 재구성

**배경**:
- 현재 `docs/`, `config/`, `data/` 구조
- 스펙 권장: `references/`, `assets/`, `scripts/`

### Issues

#### Issue 1.1: docs/ → references/ 마이그레이션
**Type**: refactor
**Priority**: P1
**Estimate**: S

**작업 내용**:
- [ ] `.claude/skills/beopsuny/docs/` → `.claude/skills/beopsuny/references/` 이름 변경
- [ ] SKILL.md 내 경로 참조 업데이트
- [ ] CLAUDE.md 내 경로 참조 업데이트

**파일**:
- `docs/user_guide.md` → `references/user_guide.md`
- `docs/contract_review_guide.md` → `references/contract_review_guide.md`
- `docs/international_guide.md` → `references/international_guide.md`

---

#### Issue 1.2: assets/ 디렉토리 생성 및 정적 데이터 이동
**Type**: refactor
**Priority**: P1
**Estimate**: M

**작업 내용**:
- [ ] `assets/` 디렉토리 생성
- [ ] 정적 데이터 파일 이동:
  - `config/law_index.yaml` → `assets/law_index.yaml`
  - `config/legal_terms.yaml` → `assets/legal_terms.yaml`
  - `config/clause_references.yaml` → `assets/clause_references.yaml`
  - `config/forms.yaml` → `assets/forms.yaml`
  - `config/checklists/` → `assets/checklists/`
- [ ] 스크립트 내 경로 상수 업데이트

**영향받는 스크립트**:
- `scripts/fetch_law.py`
- `scripts/fetch_bill.py`
- `scripts/generate_checklist.py`
- 기타 config 참조 스크립트

---

#### Issue 1.3: config/ 정리 (secrets only)
**Type**: refactor
**Priority**: P1
**Estimate**: S

**작업 내용**:
- [ ] `settings.yaml`에서 `major_laws`, `targets` 섹션 제거
- [ ] secrets 관련 필드만 유지: `oc_code`, `assembly_api_key`, `gateway`
- [ ] `settings.yaml.example` 업데이트
- [ ] 스크립트에서 삭제된 설정 대체 처리

**변경 전 settings.yaml**:
```yaml
oc_code: "xxx"
assembly_api_key: "xxx"
gateway: {...}
api: {...}           # 제거 또는 단순화
targets: {...}       # 제거 (law_index.yaml로 통합)
major_laws: {...}    # 제거 (law_index.yaml과 중복)
```

**변경 후 settings.yaml**:
```yaml
oc_code: ""
assembly_api_key: ""
gateway:
  url: ""
  api_key: ""
```

---

#### Issue 1.4: 스크립트 경로 상수 통합 리팩토링
**Type**: refactor
**Priority**: P1
**Estimate**: M

**작업 내용**:
- [ ] `scripts/common/paths.py` 또는 유사한 공통 모듈 생성
- [ ] 모든 스크립트에서 경로 상수 통합 사용
- [ ] 테스트로 경로 변경 검증

**예시**:
```python
# scripts/common/paths.py
from pathlib import Path

SKILL_ROOT = Path(__file__).parent.parent.parent
ASSETS_DIR = SKILL_ROOT / "assets"
CONFIG_DIR = SKILL_ROOT / "config"
REFERENCES_DIR = SKILL_ROOT / "references"
DATA_DIR = SKILL_ROOT / "data"
```

---

## Epic 2: SKILL.md 재구성 (Option A)

**목표**: 역할 기반 구조로 SKILL.md 재구성, 500줄 미만 유지

**배경**:
- 현재 483줄 (한계 근접)
- 중복 섹션 존재 ("핵심 원칙" ↔ "Instructions for Claude")
- Progressive Disclosure 원칙 적용 필요

### Issues

#### Issue 2.1: SKILL.md에서 Quick Reference 분리
**Type**: refactor
**Priority**: P2
**Estimate**: S

**작업 내용**:
- [ ] "Quick Reference" 섹션 → `references/quick-reference.md` 분리
- [ ] SKILL.md에서 해당 섹션 제거
- [ ] 필요 시 짧은 참조 링크만 유지

---

#### Issue 2.2: SKILL.md에서 외부 참고 사이트 분리
**Type**: refactor
**Priority**: P2
**Estimate**: S

**작업 내용**:
- [ ] "외부 참고 사이트" 섹션 → `references/external-sites.md` 분리
- [ ] SKILL.md에서 해당 섹션 제거
- [ ] 필요 시 짧은 참조 링크만 유지

---

#### Issue 2.3: 중복 섹션 통합
**Type**: refactor
**Priority**: P2
**Estimate**: M

**작업 내용**:
- [ ] "Instructions for Claude" 내용 → "핵심 원칙"으로 통합
- [ ] "필수 명령어" ↔ "Quick Reference" 중복 정리
- [ ] "기능별 명령어" → "Commands Reference"로 통합

---

#### Issue 2.4: SKILL.md 역할 기반 재구성
**Type**: refactor
**Priority**: P2
**Estimate**: L

**작업 내용**:
- [ ] 새로운 섹션 구조 적용:
  ```
  1. Overview (개요)
  2. Setup (환경 설정)
  3. Core Workflows (핵심 워크플로우)
  4. Commands Reference (명령어)
  5. Use Cases (활용 사례)
  6. Resources (참고 자료)
  ```
- [ ] 기존 내용 새 구조로 재배치
- [ ] 한글/영어 하이브리드 규칙 적용

**목표**: 350줄 이하

---

#### Issue 2.5: Frontmatter 확장
**Type**: enhancement
**Priority**: P2
**Estimate**: S

**작업 내용**:
- [ ] `license: MIT` 추가
- [ ] `compatibility` 필드 추가 (Python 3.9+, 환경변수 요구사항)
- [ ] `metadata` 필드 추가 (version, author, language)

**예시**:
```yaml
---
name: beopsuny
description: 법순이 - 한국 법령/판례 검색, 다운로드, 분석 도우미...
license: MIT
compatibility: |
  - Python 3.9+
  - 환경변수: BEOPSUNY_OC_CODE (필수)
  - 선택: BEOPSUNY_ASSEMBLY_API_KEY, BEOPSUNY_GATEWAY_URL
metadata:
  version: "2.0.0"
  author: "legal-stack"
  language: "ko"
---
```

---

## Epic 3: CI/CD 및 검증

**목표**: skills-ref validate 도구를 활용한 자동 검증 체계 구축

### Issues

#### Issue 3.1: skills-ref validate CI 워크플로우 추가
**Type**: ci
**Priority**: P2
**Estimate**: S

**작업 내용**:
- [ ] `.github/workflows/validate-skill.yml` 생성
- [ ] PR 시 자동 검증 실행
- [ ] 검증 실패 시 PR 머지 차단

**예시**:
```yaml
name: Validate Skill

on:
  pull_request:
    paths:
      - '.claude/skills/beopsuny/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install skills-ref
      - run: skills-ref validate .claude/skills/beopsuny
```

---

#### Issue 3.2: GitHub Actions 경로 업데이트
**Type**: ci
**Priority**: P1
**Estimate**: S

**작업 내용**:
- [ ] 기존 ZIP 빌드 워크플로우에서 경로 업데이트
- [ ] `config/` → `assets/` 경로 변경 반영
- [ ] `docs/` → `references/` 경로 변경 반영

---

## Epic 4: 문서화 및 마이그레이션

**목표**: 변경사항 문서화 및 기존 사용자 지원

### Issues

#### Issue 4.1: CHANGELOG 작성
**Type**: docs
**Priority**: P2
**Estimate**: S

**작업 내용**:
- [ ] `CHANGELOG.md` 생성
- [ ] 버전 2.0.0 변경사항 기록
- [ ] SemVer 정책 명시

---

#### Issue 4.2: 마이그레이션 가이드 작성
**Type**: docs
**Priority**: P3
**Estimate**: M

**작업 내용**:
- [ ] `references/migration-guide.md` 작성
- [ ] 디렉토리 구조 변경 안내
- [ ] 스크립트 경로 변경 안내
- [ ] 설정 파일 변경 안내

---

## 구현 순서 (권장)

```
Phase 1 (즉시)
├── Issue 1.1: docs/ → references/
├── Issue 1.2: assets/ 생성 및 데이터 이동
├── Issue 1.3: config/ 정리
├── Issue 1.4: 스크립트 경로 리팩토링
└── Issue 3.2: GitHub Actions 경로 업데이트

Phase 2 (중기)
├── Issue 2.1: Quick Reference 분리
├── Issue 2.2: 외부 사이트 분리
├── Issue 2.3: 중복 섹션 통합
├── Issue 2.4: SKILL.md 재구성
├── Issue 2.5: Frontmatter 확장
└── Issue 3.1: skills-ref validate CI

Phase 3 (장기)
├── Issue 4.1: CHANGELOG 작성
└── Issue 4.2: 마이그레이션 가이드
```

---

## 예상 일정 (Estimate 기준)

| Size | 예상 작업량 |
|------|-----------|
| S | 1-2시간 |
| M | 반나절 |
| L | 1일 |

**Phase 1 총 예상**: M-L (반나절~1일)
**Phase 2 총 예상**: L-XL (1-2일)
**Phase 3 총 예상**: M (반나절)

---

## 체크리스트

### Phase 1 완료 기준
- [ ] 모든 스크립트가 새 경로에서 정상 작동
- [ ] skills-ref validate 통과
- [ ] ZIP 빌드 워크플로우 정상 작동

### Phase 2 완료 기준
- [ ] SKILL.md 350줄 이하
- [ ] 모든 섹션이 역할 기반 구조로 재배치
- [ ] CI에서 자동 검증 실행

### Phase 3 완료 기준
- [ ] CHANGELOG에 모든 변경사항 기록
- [ ] 마이그레이션 가이드 완성
