# 체크리스트 유지보수 가이드

법률 체크리스트는 **시간에 민감한 정보**를 포함합니다. 정기적인 점검 없이는 낡은 정보가 오히려 해가 될 수 있습니다.

## 점검 주기

| 주기 | 시기 | 점검 항목 |
|------|------|----------|
| **분기** | 1/4/7/10월 첫째 주 | 수치 변경, 행정규칙 업데이트 |
| **연간** | 1월 | 전체 법령 개정 여부, 조문 번호 확인 |
| **수시** | 주요 법령 개정 시 | 해당 체크리스트 즉시 업데이트 |

---

## 체크리스트별 점검 항목

### 1. labor_hr.yaml (노동/인사)

**변경 가능성 높은 항목:**
| 항목 | 현재 값 | 점검 방법 |
|------|---------|----------|
| 장애인 의무고용률 | 민간 3.1%, 공공 3.8% | [한국장애인고용공단](https://www.kead.or.kr) |
| 최저임금 | (금액 미포함) | [최저임금위원회](https://www.minimumwage.go.kr) |
| 규모별 적용 기준 | 5/10/50/300인 | 근로기준법 시행령 확인 |

**점검 쿼리:**
```
"장애인 의무고용률 2025" site:moel.go.kr
"근로기준법 시행령 개정" 2025
```

---

### 2. serious_accident.yaml (중대재해처벌법)

**변경 가능성 높은 항목:**
| 항목 | 현재 값 | 점검 방법 |
|------|---------|----------|
| 적용 대상 | 5인 이상 전 사업장 | 법 제3조 확인 |
| 처벌 수위 | 1년↑ 징역/10억 벌금 | 법 제6조, 제7조 |
| 법인 벌금 | 50억/10억 | 법 제11조 |

**점검 쿼리:**
```
"중대재해처벌법 개정" 2025
"중대재해처벌법 시행령 개정" site:law.go.kr
```

**주의:** 중대재해처벌법은 정치적 이슈로 개정 논의가 활발함. 뉴스 모니터링 필요.

---

### 3. privacy_compliance.yaml (개인정보보호)

**변경 가능성 높은 항목:**
| 항목 | 현재 값 | 점검 방법 |
|------|---------|----------|
| 과징금 상한 | 전체 매출 4% | 개인정보보호법 제64조의2 |
| 안전조치 기준 | 고시 기준 | [개인정보보호위원회](https://www.pipc.go.kr) 고시 |
| 국외이전 요건 | 제28조의8 | 개정 여부 확인 |

**점검 쿼리:**
```
"개인정보보호법 개정" 2025
"개인정보 안전성 확보조치 기준 고시" site:pipc.go.kr
```

---

### 4. fair_trade.yaml (공정거래)

**변경 가능성 높은 항목:**
| 항목 | 현재 값 | 점검 방법 |
|------|---------|----------|
| 과징금 부과기준 | 관련매출 10% 등 | 공정거래법 시행령 |
| 기업결합 신고 기준 | 자산/매출 3천억 등 | 법 제11조 |
| 하도급 서면발급 기준 | 30일 | 하도급법 제3조 |

**점검 쿼리:**
```
"공정거래법 시행령 개정" 2025 과징금
"하도급법 개정" site:ftc.go.kr
```

---

### 5. contract_review.yaml (계약서 검토)

**변경 가능성 높은 항목:**
| 항목 | 현재 값 | 점검 방법 |
|------|---------|----------|
| 상가임대차 갱신기간 | 10년 | 상가건물임대차보호법 제10조 |
| 차임 증액 상한 | 연 5% | 법 제11조 |
| 약관규제법 조항 | 제6조~제14조 | 조문 번호 변경 여부 |

**점검 쿼리:**
```
"상가건물임대차보호법 개정" 2025
"약관규제법 개정" site:law.go.kr
```

---

### 6. investment_due_diligence.yaml (투자 실사)

**변경 가능성 높은 항목:**
| 항목 | 현재 값 | 점검 방법 |
|------|---------|----------|
| 기업결합 신고 기준 | 공정거래법 기준 | 공정거래법 제11조 |
| 외국인투자 신고 | 외국인투자촉진법 | 산업부 고시 |

**비교적 안정적:** 실사 항목 자체는 법령 변경보다 실무 관행 변화에 영향받음.

---

### 7. startup.yaml (스타트업 설립)

**변경 가능성 높은 항목:**
| 항목 | 현재 값 | 점검 방법 |
|------|---------|----------|
| 법인설립 등기 | 상법 제288조 등 | 조문 번호 확인 |
| 4대보험 신고 | 고용보험법 등 | 신고 기한 변경 여부 |

**비교적 안정적:** 설립 절차는 변경 빈도 낮음.

---

## 점검 프로세스

### Step 1: 변경 여부 확인
```bash
# 법제처 법령 검색
python .claude/skills/beopsuny/scripts/fetch_law.py search "개정" --days 90

# 웹검색 (Claude에게 요청)
"[법령명] 개정 2025" site:law.go.kr
"[법령명] 시행령 개정" site:moleg.go.kr
```

### Step 2: 변경 내용 반영
1. 해당 YAML 파일 수정
2. `last_updated` 필드 업데이트
3. 변경 사유 커밋 메시지에 기록

### Step 3: 변경 이력 기록
```yaml
# YAML 파일 상단에 추가 권장
changelog:
  - date: "2025-01-15"
    changes: "장애인 의무고용률 3.1% → 3.3% 반영 (2027년 시행)"
    source: "고용노동부 고시 제2025-XX호"
```

---

## 자동화 (선택)

### GitHub Issue 자동 생성
`.github/workflows/checklist-review.yml`:
```yaml
name: Quarterly Checklist Review
on:
  schedule:
    - cron: '0 9 1 1,4,7,10 *'  # 1/4/7/10월 1일 09:00
jobs:
  create-issue:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/github-script@v6
        with:
          script: |
            const date = new Date();
            const quarter = Math.ceil((date.getMonth() + 1) / 3);
            github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: `Q${quarter} ${date.getFullYear()} 체크리스트 정기 점검`,
              body: `## 점검 항목\n- [ ] labor_hr.yaml\n- [ ] serious_accident.yaml\n- [ ] privacy_compliance.yaml\n- [ ] fair_trade.yaml\n- [ ] contract_review.yaml\n- [ ] investment_due_diligence.yaml\n- [ ] startup.yaml\n\n참고: assets/checklists/MAINTENANCE.md`,
              labels: ['maintenance', 'checklist']
            });
```

---

## 법령 모니터링 리소스

| 리소스 | URL | 용도 |
|--------|-----|------|
| 법제처 법령정보 | https://www.law.go.kr | 법령 원문, 연혁 |
| 국회 의안정보 | https://likms.assembly.go.kr/bill | 개정안 동향 |
| 고용노동부 | https://www.moel.go.kr | 노동법 고시 |
| 공정거래위원회 | https://www.ftc.go.kr | 공정거래 고시 |
| 개인정보보호위원회 | https://www.pipc.go.kr | 개인정보 고시 |
| 법률신문 | https://www.lawtimes.co.kr | 법령 개정 뉴스 |

---

## 변경 이력

| 날짜 | 변경 내용 |
|------|----------|
| 2025-12-09 | 최초 작성 |
