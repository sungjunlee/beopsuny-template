# Quick Reference (빠른 참조)

법순이 자주 사용하는 명령어 치트시트.

## 법령 검색

```bash
# 정확한 법령 검색
fetch_law.py exact "개인정보보호법"
fetch_law.py exact "상법" --with-admrul  # 행정규칙 포함

# 키워드 검색
fetch_law.py search "과징금" --type admrul  # 행정규칙
fetch_law.py search "개인정보" --type law   # 법령
```

## 판례 검색

```bash
fetch_law.py cases "손해배상"
fetch_law.py cases "해고" --court 대법원 --from 20240101
```

## 최근 개정

```bash
fetch_law.py recent --days 30
fetch_law.py recent --days 7 --date-type anc   # 공포일 기준
```

## 국회 의안

```bash
fetch_bill.py track "개인정보보호법"
fetch_bill.py pending --keyword 민법
```

## 체크리스트

```bash
fetch_law.py checklist list                    # 목록 보기
fetch_law.py checklist show startup            # 스타트업 설립
fetch_law.py checklist show privacy_compliance # 개인정보 점검
fetch_law.py checklist show fair_trade         # 공정거래
```

## WebSearch 치트시트

| 목적 | 쿼리 템플릿 |
|------|------------|
| 제재 사례 | `"{법령} 과징금 2024 2025 site:lawtimes.co.kr"` |
| 정부 스탠스 | `"{부처} {법령} 제재 2025"` |
| 판례 변경 | `"{법령} 대법원 전원합의체 2024 2025"` |
| 법제처 해석 | `"{법령} 법제처 유권해석 2024 2025"` |

## 주요 부처 코드

| 부처 | 코드 | 관련 법령 |
|------|------|----------|
| 공정거래위원회 | `ftc` | 공정거래법, 하도급법 |
| 개인정보보호위원회 | `pipc` | 개인정보보호법 |
| 고용노동부 | `moel` | 근로기준법, 산재법 |
| 금융위원회 | `fsc` | 자본시장법 |

## law_index.yaml 주요 ID

| 법령 | 행정규칙 | ID |
|------|----------|-----|
| 개인정보보호법 | 과징금_부과기준 | `2100000229342` |
| 개인정보보호법 | 안전성_확보조치 | `2100000265956` |
| 공정거래법 | 과징금_부과기준 | `2100000246412` |
| 최저임금법 | 2025년_고시 | `2100000245668` |

**전체 목록**: `assets/law_index.yaml`

---

[← SKILL.md로 돌아가기](../SKILL.md)
