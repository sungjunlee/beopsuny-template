# Permits Data Collection Tools

기업 허가/신고 데이터 수집 및 permits.yaml 생성 도구

## 개요

이 디렉토리는 `.claude/skills/beopsuny/assets/permits.yaml` 생성을 위한 데이터 수집 도구입니다.
스킬 런타임과 분리되어 있으며, 1회성 데이터 수집 및 갱신 용도로 사용됩니다.

## 파일 구조

```
tools/permits/
├── README.md           # 이 파일
├── seed_data.yaml      # 수동 큐레이션된 인허가 정보
└── generate_permits.py # permits.yaml 생성 스크립트
```

## 사용법

### 1. 시드 데이터 확인/수정

`seed_data.yaml`에서 인허가 정보를 확인하고 필요시 수정합니다.

### 2. permits.yaml 생성

```bash
cd tools/permits
python generate_permits.py
```

출력 파일: `../../.claude/skills/beopsuny/assets/permits.yaml`

### 3. 커스텀 출력 경로

```bash
python generate_permits.py --output /path/to/permits.yaml
```

## 데이터 소스

| 소스 | 용도 | 접근 방식 |
|------|------|----------|
| 정부24 (gov.kr) | 민원 상세정보 | 수동 조회 |
| 찾기쉬운법령 (easylaw.go.kr) | 인허가 가이드 | 수동 조회 |
| 공공데이터포털 (data.go.kr) | 민원안내정보 | CSV 다운로드 (선택) |

## 데이터 갱신 주기

- **권장**: 분기별 (법령 개정 주기 고려)
- **자동화**: GitHub Actions `check-permit-updates` job

## 주의사항

- 시드 데이터는 수동 큐레이션됨 (자동 크롤링 아님)
- 법령 개정 시 `law_id` 및 `article` 변경 가능
- 수수료, 구비서류는 변동 가능성 높음 (volatile_items)

## 관련 파일

- 최종 산출물: `.claude/skills/beopsuny/assets/permits.yaml`
- 법령 인덱스: `.claude/skills/beopsuny/assets/law_index.yaml`
- 유지보수 스크립트: `.claude/skills/beopsuny/scripts/maintenance/validate_permits.py`
