---
name: beopsuny
description: 한국 법령/판례를 검색, 다운로드, 분석합니다. 법률 조문 확인, 판례 검색, 개정 확인, 시행령/시행규칙 조회 시 자동 활성화됩니다. Searches Korean laws, cases, and regulations via National Law Information Center API.
---

# Beopsuny (법순이) - 한국 법령 리서치 도우미

국가법령정보센터 Open API를 활용하여 한국 법령과 판례를 검색, 다운로드, 분석하는 Claude Code skill입니다.

## 핵심 원칙

1. **정확한 인용**: 모든 법적 의견은 구체적인 조문/판례 인용 필수
   - 법령: "민법 제750조", "개인정보보호법 제15조제1항"
   - 판례: "대법원 2023. 1. 12. 선고 2022다12345 판결"

2. **검증 가능한 링크 제공**: 모든 인용에 law.go.kr 링크 포함

3. **시행일 확인**: 현행 여부와 시행일자 반드시 명시

4. **면책 고지**: 정식 법률 자문은 변호사 상담 필요함을 안내

## 기능

### 1. 법령 검색 (search)
```bash
python scripts/fetch_law.py search "민법"
python scripts/fetch_law.py search "개인정보" --type law
python scripts/fetch_law.py search "개인정보" --sort date   # 날짜순 정렬
python scripts/fetch_law.py search "횡령" --type prec       # 판례 검색
python scripts/fetch_law.py search "서울시" --type ordin    # 자치법규
python scripts/fetch_law.py search "보건" --type admrul     # 행정규칙
python scripts/fetch_law.py search "개인정보" --type expc   # 법령해석례
python scripts/fetch_law.py search "기본권" --type detc     # 헌재결정례
```

### 2. 판례 검색 (cases)
```bash
python scripts/fetch_law.py cases "불법행위 손해배상"
python scripts/fetch_law.py cases "근로계약 해고" --court 대법원
python scripts/fetch_law.py cases "개인정보" --from 20240101
```

### 3. 법령/판례 다운로드 (fetch)
```bash
python scripts/fetch_law.py fetch --id 001706
python scripts/fetch_law.py fetch --name "민법"
python scripts/fetch_law.py fetch --name "민법" --with-decree  # 시행령 포함
python scripts/fetch_law.py fetch --case "2022다12345"         # 판례 다운로드
python scripts/fetch_law.py fetch --name "민법" --force        # 캐시 무시
```

### 4. 최근 개정 법령 조회 (recent)
```bash
python scripts/fetch_law.py recent --days 30
python scripts/fetch_law.py recent --from 20250101 --to 20251231
```

### 5. 법령 파싱 (parse)
```bash
python scripts/parse_law.py data/raw/민법_001706.xml
python scripts/parse_law.py data/raw/민법_001706.xml --article 750
```

### 6. 개정 비교 (compare)
```bash
python scripts/compare_law.py data/raw/old.xml data/raw/new.xml --name "민법"
```

### 7. 링크 생성 (link)
```bash
python scripts/gen_link.py law "민법" --article 750
python scripts/gen_link.py case "2022다12345"
python scripts/gen_link.py search "개인정보보호법"
python scripts/gen_link.py history "민법" --id 001706    # 연혁법령 링크
python scripts/gen_link.py decree "개인정보보호법"        # 시행령/시행규칙 링크
```

## 검색 대상 코드 (target)

| 코드 | 대상 | 설명 |
|------|------|------|
| `law` | 법령 | 법률, 대통령령, 부령 등 |
| `prec` | 판례 | 대법원, 하급심 판결 |
| `ordin` | 자치법규 | 조례, 규칙 |
| `admrul` | 행정규칙 | 훈령, 예규, 고시 |
| `expc` | 법령해석례 | 법제처 해석 |
| `detc` | 헌재결정례 | 헌법재판소 결정 |

## 주요 법률 분야 검색 가이드

### IT/디지털 법률
- 개인정보보호법, 정보통신망법, 전자금융거래법, 전자서명법
- 검색어: "개인정보", "정보통신", "전자금융", "플랫폼"

### 노동법
- 근로기준법, 최저임금법, 산업안전보건법
- 검색어: "근로계약", "해고", "임금", "산재"

### 상법/기업법
- 상법, 공정거래법, 자본시장법
- 검색어: "주주", "이사", "합병", "공정거래"

### 형사법
- 형법, 특정범죄가중처벌법, 도로교통법
- 검색어: "사기", "횡령", "배임", "음주운전"

## 링크 형식

### 법령 직접 링크
```
https://www.law.go.kr/법령/민법
https://www.law.go.kr/법령/민법/제750조
https://www.law.go.kr/법령/민법시행령
https://www.law.go.kr/법령/개인정보보호법/제15조
```

### 판례 검색 링크
```
https://www.law.go.kr/판례/(2022다12345)
https://glaw.scourt.go.kr (대법원 종합법률정보)
https://casenote.kr (케이스노트 - AI 판례 검색)
https://bigcase.ai (빅케이스 - 유사 판례 추천)
```

## 데이터 저장 위치

- `data/raw/` - 원본 XML 파일
- `data/parsed/` - 파싱된 Markdown 파일

## Skill 폴더 위치

이 skill의 스크립트와 데이터는 다음 위치에 있습니다:
- **Skill 폴더**: `.claude/skills/beopsuny/`
- **스크립트**: `.claude/skills/beopsuny/scripts/`
- **데이터**: `.claude/skills/beopsuny/data/`

스크립트 실행 시 skill 폴더로 이동 후 실행:
```bash
cd .claude/skills/beopsuny && python3 scripts/fetch_law.py search "민법"
```

또는 절대 경로로 실행:
```bash
python3 .claude/skills/beopsuny/scripts/fetch_law.py search "민법"
```

## Instructions for Claude

### 법령 관련 질문 처리
1. `scripts/fetch_law.py`로 법령 데이터 조회/다운로드
2. 이미 다운로드된 파일이 있으면 재사용 (Glob으로 `data/raw/` 확인)
3. 조문 인용 시 `scripts/gen_link.py`로 검증 가능한 링크 생성
4. **시행일자 반드시 확인** - 미시행 법령은 명확히 표시

### 판례 관련 질문 처리
1. `scripts/fetch_law.py cases` 또는 `search --type prec`로 검색
2. 판례 인용 형식: "대법원 YYYY. M. D. 선고 XXXX다XXXXX 판결"
3. 판례 검색 링크 제공 (law.go.kr, casenote.kr)

### 출력 형식
```markdown
## 민법 제750조 (불법행위의 내용)

> 고의 또는 과실로 인한 위법행위로 타인에게 손해를 가한 자는 그 손해를 배상할 책임이 있다.

- **시행일**: 2025. 1. 31.
- **링크**: https://www.law.go.kr/법령/민법/제750조

### 관련 판례
- 대법원 2023. 5. 18. 선고 2022다12345 판결
  - [판례 검색](https://www.law.go.kr/판례/(2022다12345))
```

### 시행령/시행규칙 안내
법률 조회 시 관련 시행령/시행규칙도 함께 안내:
- 민법 → 민법 시행령 (없음), 가족관계의 등록 등에 관한 규칙
- 개인정보보호법 → 개인정보보호법 시행령, 시행규칙

### 면책 고지
법률 분석 답변 마지막에 다음 문구 포함:
> ⚠️ **참고**: 이 정보는 일반적인 법률 정보 제공 목적이며, 구체적인 법률 문제는 변호사와 상담하시기 바랍니다.

## 외부 참고 사이트

| 사이트 | URL | 용도 |
|--------|-----|------|
| 국가법령정보센터 | law.go.kr | 법령/판례 원문 |
| 법제처 | moleg.go.kr | 법령해석, 입법예고 |
| 대법원 종합법률정보 | glaw.scourt.go.kr | 판례 원문 |
| 헌법재판소 | ccourt.go.kr | 헌재 결정문 |
| 케이스노트 | casenote.kr | AI 판례 검색 |
| 빅케이스 | bigcase.ai | 유사 판례 추천 |
| 국민참여입법센터 | opinion.lawmaking.go.kr | 입법예고 |
