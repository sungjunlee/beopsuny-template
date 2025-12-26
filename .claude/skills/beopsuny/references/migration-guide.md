# v1.x → v2.0 마이그레이션 가이드

> v2.0에서 디렉토리 구조가 변경되었습니다. 이 가이드를 따라 기존 설치를 업데이트하세요.

## 목차

1. [변경사항 요약](#1-변경사항-요약)
2. [디렉토리 구조 변경](#2-디렉토리-구조-변경)
3. [스크립트 경로 업데이트](#3-스크립트-경로-업데이트)
4. [설정 파일 정리](#4-설정-파일-정리)
5. [단계별 마이그레이션](#5-단계별-마이그레이션)
6. [문제 해결](#6-문제-해결)

---

## 1. 변경사항 요약

### 마이그레이션이 필요한 경우

다음 중 하나에 해당하면 마이그레이션이 필요합니다:

- [ ] 스크립트에서 `docs/` 폴더를 직접 참조
- [ ] 스크립트에서 `config/law_index.yaml` 등 데이터 파일 참조
- [ ] `settings.yaml`에서 `major_laws`, `targets` 설정 사용
- [ ] 커스텀 스크립트에서 하드코딩된 경로 사용

### 마이그레이션이 필요 없는 경우

- 공식 스크립트만 사용 (자동으로 새 경로 사용)
- 명령어 인터페이스에 변경 없음

---

## 2. 디렉토리 구조 변경

### Before/After 비교

```
v1.x                              v2.0
────────────────────────────────────────────────────────────────
beopsuny/                         beopsuny/
├── SKILL.md                      ├── SKILL.md (restructured)
├── config/                       ├── config/
│   ├── settings.yaml             │   ├── settings.yaml (secrets only)
│   ├── law_index.yaml        ──► │   └── settings.yaml.example
│   ├── legal_terms.yaml          │
│   ├── clause_references.yaml    ├── assets/ (NEW)
│   ├── forms.yaml                │   ├── law_index.yaml
│   └── checklists/               │   ├── legal_terms.yaml
├── docs/                         │   ├── clause_references.yaml
│   ├── user_guide.md             │   ├── forms.yaml
│   ├── contract_review_guide.md  │   └── checklists/
│   └── ...                       │
│                                 ├── references/ (renamed)
│                                 │   ├── user_guide.md
│                                 │   ├── contract_review_guide.md
│                                 │   ├── quick-reference.md (NEW)
│                                 │   ├── external-sites.md (NEW)
│                                 │   └── migration-guide.md (this file)
│                                 │
└── scripts/                      └── scripts/
                                      └── common/
                                          └── paths.py (NEW)
```

### 파일 이전 매핑

| v1.x 경로 | v2.0 경로 | 비고 |
|-----------|-----------|------|
| `docs/user_guide.md` | `references/user_guide.md` | 이름 변경 |
| `docs/contract_review_guide.md` | `references/contract_review_guide.md` | 이름 변경 |
| `docs/international_guide.md` | `references/international_guide.md` | 이름 변경 |
| `config/law_index.yaml` | `assets/law_index.yaml` | 데이터 분리 |
| `config/legal_terms.yaml` | `assets/legal_terms.yaml` | 데이터 분리 |
| `config/clause_references.yaml` | `assets/clause_references.yaml` | 데이터 분리 |
| `config/forms.yaml` | `assets/forms.yaml` | 데이터 분리 |
| `config/checklists/` | `assets/checklists/` | 디렉토리 이동 |

---

## 3. 스크립트 경로 업데이트

### 기존 방식 (v1.x)

```python
# 하드코딩된 경로
config_path = Path(__file__).parent.parent / "config" / "law_index.yaml"
```

### 새로운 방식 (v2.0)

```python
# 중앙 집중식 경로 관리
from common.paths import LAW_INDEX_PATH, ASSETS_DIR, CONFIG_PATH

# 사용 예시
with open(LAW_INDEX_PATH) as f:
    law_index = yaml.safe_load(f)
```

### 사용 가능한 경로 상수

`scripts/common/paths.py`에서 제공:

```python
# 기본 디렉토리
SKILL_DIR       # beopsuny/
SCRIPT_DIR      # beopsuny/scripts/

# 설정 (secrets only)
CONFIG_DIR      # beopsuny/config/
CONFIG_PATH     # beopsuny/config/settings.yaml

# 정적 데이터
ASSETS_DIR          # beopsuny/assets/
LAW_INDEX_PATH      # beopsuny/assets/law_index.yaml
LEGAL_TERMS_PATH    # beopsuny/assets/legal_terms.yaml
CLAUSE_REFS_PATH    # beopsuny/assets/clause_references.yaml
FORMS_PATH          # beopsuny/assets/forms.yaml
CHECKLISTS_DIR      # beopsuny/assets/checklists/

# 문서
REFERENCES_DIR      # beopsuny/references/

# 런타임 데이터
DATA_DIR            # beopsuny/data/
DATA_RAW_DIR        # beopsuny/data/raw/
DATA_PARSED_DIR     # beopsuny/data/parsed/
```

---

## 4. 설정 파일 정리

### 제거된 설정

`settings.yaml`에서 다음 항목이 제거되었습니다:

| 항목 | 이유 | 대안 |
|------|------|------|
| `major_laws` | 정적 데이터 | `assets/law_index.yaml` 사용 |
| `targets` | 정적 데이터 | `assets/law_index.yaml` 사용 |
| `api.base_url` | 코드 내 상수화 | `paths.py`의 `API_BASE_URL` |
| `api.timeout` | 코드 내 상수화 | `paths.py`의 `API_TIMEOUT` |

### v2.0 settings.yaml 구조

```yaml
# secrets only - API 키만 포함
oc_code: "your_oc_code"
assembly_api_key: "your_api_key"  # 선택

# 해외 접속용 (선택)
gateway:
  url: "https://your-proxy.workers.dev"
  api_key: "gateway_key"
```

---

## 5. 단계별 마이그레이션

### 5.1 백업 생성

```bash
cd .claude/skills/beopsuny

# 설정 백업
cp config/settings.yaml config/settings.yaml.backup

# 커스텀 수정 확인
git status
git diff
```

### 5.2 최신 버전 가져오기

```bash
# 원격 변경사항 가져오기
git fetch origin

# v2.0 태그로 업데이트 (또는 main 브랜치)
git checkout v2.0.0
# 또는
git pull origin main
```

### 5.3 설정 파일 정리

```bash
# 기존 설정에서 API 키만 추출
# settings.yaml.backup에서 oc_code, assembly_api_key 복사

# 새 settings.yaml 생성
cp config/settings.yaml.example config/settings.yaml
# API 키 입력
```

### 5.4 커스텀 스크립트 업데이트

커스텀 스크립트가 있다면:

```python
# 변경 전
config_path = Path(__file__).parent.parent / "config" / "law_index.yaml"

# 변경 후
from common.paths import LAW_INDEX_PATH
# LAW_INDEX_PATH 직접 사용
```

### 5.5 검증

```bash
# 스크립트 정상 동작 확인
python scripts/fetch_law.py --help
python scripts/fetch_bill.py --help

# 검색 테스트
python scripts/fetch_law.py exact "민법"
```

---

## 6. 문제 해결

### Q1: `ModuleNotFoundError: No module named 'common'`

**원인**: Python 경로에 `scripts/` 디렉토리가 없음

**해결**:
```bash
cd .claude/skills/beopsuny/scripts
python fetch_law.py --help
```

또는 `PYTHONPATH` 설정:
```bash
export PYTHONPATH="${PYTHONPATH}:.claude/skills/beopsuny/scripts"
```

### Q2: `FileNotFoundError: config/law_index.yaml`

**원인**: v1.x 경로를 하드코딩한 스크립트

**해결**: `assets/law_index.yaml`로 경로 변경 또는 `common.paths` import

### Q3: `KeyError: 'major_laws'`

**원인**: settings.yaml에서 제거된 설정 참조

**해결**: `assets/law_index.yaml`에서 직접 로드
```python
from common.paths import LAW_INDEX_PATH
import yaml

with open(LAW_INDEX_PATH) as f:
    law_index = yaml.safe_load(f)
major_laws = law_index.get("major_laws", {})
```

### Q4: 이전 버전으로 롤백하려면?

```bash
# v1.x 태그로 복원
git checkout v1.0.0

# 또는 특정 커밋
git checkout <commit-hash>
```

---

## 관련 문서

- [CHANGELOG.md](../CHANGELOG.md) - 전체 변경 이력
- [사용자 가이드](user_guide.md) - 전체 기능 설명
- [빠른 참조](quick-reference.md) - 자주 쓰는 명령어

---

## 도움이 필요하신가요?

- GitHub Issues: 버그 리포트 및 기능 요청
- SKILL.md: 전체 스킬 문서

---

[← SKILL.md로 돌아가기](../SKILL.md)
