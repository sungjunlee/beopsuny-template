# geo-fetch: 지역 기반 HTTP Fetch Gateway

## 프로젝트 개요

### 한 줄 설명
특정 국가/지역 IP에서만 접근 가능한 웹사이트/API를 대신 fetch해주는 경량 HTTP 게이트웨이

### 문제 정의

많은 정부 API와 웹서비스가 **지역 IP 제한**을 둠:
- 한국: law.go.kr, korea.kr, open.assembly.go.kr (해외 IP 차단)
- 일본: 일부 정부/금융 서비스
- 중국: 바이두, 위챗 API
- 미국: 일부 스트리밍/API

**기존 솔루션의 한계**:
| 솔루션 | 문제점 |
|--------|--------|
| Residential Proxy (Bright Data 등) | 유료, 복잡, VPN 탐지로 차단 |
| VPN | 클라이언트 설치 필요 |
| Cloudflare Workers | 리전 선택 불가 |
| CORS Proxy | 특정 국가 IP 없음 |

### 해결책

해당 국가에 배치된 서버가 **HTTP API 형태로** 대신 fetch:

```
[클라이언트 (해외)]
    → GET https://kr.geo-fetch.io/fetch?url=http://law.go.kr/...
    → [한국 서버가 대신 fetch]
    → [결과 반환]
```

### 주요 사용 사례

1. **beopsuny (법순이)**: Claude Code Web에서 한국 법령 API 접근
2. **해외 개발자**: 한국 정부 Open API 사용
3. **크롤링/스크래핑**: 지역 제한 사이트 데이터 수집
4. **API 테스트**: 다양한 지역에서 서비스 응답 확인

---

## 기술 스펙

### 기본 정보

| 항목 | 값 |
|------|-----|
| 언어 | Python 3.11+ |
| 의존성 | 표준 라이브러리만 (외부 패키지 없음) |
| Docker 이미지 크기 | < 50MB (Alpine 기반) |
| 기본 포트 | 8080 |
| 라이선스 | MIT |

### API 엔드포인트

#### 1. GET /fetch - URL Fetch (기본)

```bash
GET /fetch?url=<encoded_url>[&options...]
```

**파라미터**:
| 파라미터 | 필수 | 설명 | 예시 |
|---------|------|------|------|
| `url` | ✅ | fetch할 URL (URL 인코딩) | `http%3A%2F%2Flaw.go.kr%2F...` |
| `format` | ❌ | 응답 형식 (`raw`, `json`) | `raw` (기본) |
| `timeout` | ❌ | 타임아웃 초 | `30` (기본) |
| `headers` | ❌ | 응답 헤더 포함 여부 | `true` / `false` |

**예시**:
```bash
# 기본 사용 (raw 응답)
curl "https://kr.geo-fetch.io/fetch?url=http://www.law.go.kr/DRF/lawSearch.do?query=민법"

# JSON 래핑
curl "https://kr.geo-fetch.io/fetch?url=http://example.com&format=json"
```

**응답 (format=raw)**:
```
원본 응답 그대로 반환
Content-Type도 원본 유지
```

**응답 (format=json)**:
```json
{
  "success": true,
  "status_code": 200,
  "headers": {
    "Content-Type": "text/xml; charset=utf-8",
    "Content-Length": "12345"
  },
  "body": "...",
  "meta": {
    "url": "http://www.law.go.kr/...",
    "fetched_at": "2025-12-06T06:00:00Z",
    "latency_ms": 150,
    "server_ip": "121.x.x.x",
    "server_location": "kr"
  }
}
```

#### 2. POST /fetch - Body 포함 요청

```bash
POST /fetch?url=<encoded_url>
Content-Type: application/json

{
  "method": "POST",
  "headers": {
    "Authorization": "Bearer xxx"
  },
  "body": "..."
}
```

#### 3. GET /health - 헬스체크

```bash
GET /health
```

**응답**:
```json
{
  "status": "ok",
  "version": "1.0.0",
  "location": "kr",
  "public_ip": "121.x.x.x",
  "uptime_seconds": 12345
}
```

#### 4. GET /info - 서버 정보

```bash
GET /info
```

**응답**:
```json
{
  "service": "geo-fetch",
  "version": "1.0.0",
  "location": {
    "country": "KR",
    "city": "Seoul",
    "ip": "121.x.x.x"
  },
  "limits": {
    "rate_limit": "100/min",
    "max_response_size": "10MB",
    "timeout": 30
  },
  "allowed_domains": ["*"]
}
```

---

## 보안

### API 키 인증

```bash
# 헤더 방식 (권장)
curl -H "X-API-Key: your-secret-key" "https://kr.geo-fetch.io/fetch?url=..."

# 쿼리 파라미터 방식
curl "https://kr.geo-fetch.io/fetch?url=...&api_key=your-secret-key"
```

### 환경변수

| 변수 | 필수 | 설명 | 기본값 |
|------|------|------|--------|
| `API_KEY` | ❌ | API 키 (없으면 인증 비활성화) | - |
| `ALLOWED_DOMAINS` | ❌ | 허용 도메인 (쉼표 구분) | `*` (전체) |
| `BLOCKED_DOMAINS` | ❌ | 차단 도메인 (쉼표 구분) | - |
| `RATE_LIMIT` | ❌ | 분당 요청 제한 | `100` |
| `MAX_RESPONSE_SIZE` | ❌ | 최대 응답 크기 | `10485760` (10MB) |
| `TIMEOUT` | ❌ | 기본 타임아웃 (초) | `30` |
| `PORT` | ❌ | 서버 포트 | `8080` |
| `LOG_LEVEL` | ❌ | 로그 레벨 | `INFO` |

### 도메인 제한 예시

```bash
# 한국 정부 API만 허용
ALLOWED_DOMAINS=law.go.kr,korea.kr,open.assembly.go.kr

# 특정 도메인 차단
BLOCKED_DOMAINS=evil.com,malware.org
```

---

## Docker 배포

### Dockerfile

```dockerfile
FROM python:3.12-alpine

LABEL maintainer="sungjunlee"
LABEL description="Geo-restricted HTTP Fetch Gateway"

# 메타데이터
ARG VERSION=1.0.0
ENV VERSION=${VERSION}

# 앱 복사
COPY geo_fetch.py /app/
WORKDIR /app

# 환경변수 기본값
ENV PORT=8080
ENV TIMEOUT=30
ENV RATE_LIMIT=100
ENV LOG_LEVEL=INFO

EXPOSE 8080

# 헬스체크
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

CMD ["python", "-u", "geo_fetch.py"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  geo-fetch:
    image: sungjunlee/geo-fetch:latest
    container_name: geo-fetch-kr
    restart: always
    ports:
      - "8080:8080"
    environment:
      - API_KEY=${GEO_FETCH_API_KEY:-}
      - ALLOWED_DOMAINS=law.go.kr,korea.kr,open.assembly.go.kr,opinion.lawmaking.go.kr
      - RATE_LIMIT=100
      - TIMEOUT=30
      - LOG_LEVEL=INFO
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:8080/health"]
      interval: 30s
      timeout: 5s
      retries: 3
```

### Portainer Stack 배포

```yaml
version: '3.8'

services:
  geo-fetch:
    image: sungjunlee/geo-fetch:latest
    container_name: geo-fetch-kr
    restart: always
    ports:
      - "8080:8080"
    environment:
      - API_KEY=your-secret-api-key
      - ALLOWED_DOMAINS=*
      - RATE_LIMIT=100
    network_mode: host  # 필요시
```

---

## 클라이언트 사용법

### cURL

```bash
# 기본
curl "https://kr.geo-fetch.io/fetch?url=http://law.go.kr/..."

# API 키 포함
curl -H "X-API-Key: secret" "https://kr.geo-fetch.io/fetch?url=..."

# JSON 형식
curl "https://kr.geo-fetch.io/fetch?url=...&format=json"
```

### Python

```python
import urllib.request
import urllib.parse

def geo_fetch(url: str, gateway: str = "https://kr.geo-fetch.io", api_key: str = None) -> str:
    """geo-fetch 게이트웨이를 통해 URL fetch"""
    fetch_url = f"{gateway}/fetch?url={urllib.parse.quote(url, safe='')}"

    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key

    req = urllib.request.Request(fetch_url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8")

# 사용
content = geo_fetch("http://www.law.go.kr/DRF/lawSearch.do?query=민법")
```

### JavaScript/Node.js

```javascript
async function geoFetch(url, gateway = "https://kr.geo-fetch.io", apiKey = null) {
  const fetchUrl = `${gateway}/fetch?url=${encodeURIComponent(url)}`;

  const headers = {};
  if (apiKey) {
    headers["X-API-Key"] = apiKey;
  }

  const response = await fetch(fetchUrl, { headers });
  return await response.text();
}

// 사용
const content = await geoFetch("http://www.law.go.kr/...");
```

---

## beopsuny 통합

### proxy_utils.py 수정

```python
# 기존 (HTTP 프록시 방식) - 작동 안 함
def fetch_via_http_proxy(url, proxy_url, ...):
    proxy_handler = urllib.request.ProxyHandler({"http": proxy_url})
    ...

# 신규 (geo-fetch 게이트웨이 방식)
def fetch_via_gateway(url: str, gateway_url: str, api_key: str = None, timeout: int = 30) -> str:
    """geo-fetch 게이트웨이를 통해 URL fetch

    Args:
        url: fetch할 URL
        gateway_url: 게이트웨이 URL (예: https://kr.geo-fetch.io)
        api_key: API 키 (선택)
        timeout: 타임아웃 (초)

    Returns:
        응답 본문
    """
    fetch_url = f"{gateway_url}/fetch?url={urllib.parse.quote(url, safe='')}"

    headers = {"User-Agent": "Beopsuny/1.0"}
    if api_key:
        headers["X-API-Key"] = api_key

    req = urllib.request.Request(fetch_url, headers=headers)

    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8")
```

### settings.yaml 설정

```yaml
# 기존 (프록시 방식)
proxy:
  type: "http"
  url: "http://proxy:3128"

# 신규 (게이트웨이 방식)
gateway:
  url: "https://kr.geo-fetch.io"
  api_key: "your-secret-key"  # 선택
```

### 환경변수

```bash
# 기존
export BEOPSUNY_PROXY_TYPE=http
export BEOPSUNY_PROXY_URL=http://proxy:3128

# 신규
export BEOPSUNY_GATEWAY_URL=https://kr.geo-fetch.io
export BEOPSUNY_GATEWAY_API_KEY=your-secret-key
```

---

## 프로젝트 구조

```
geo-fetch/
├── geo_fetch.py           # 메인 서버 코드 (단일 파일)
├── Dockerfile             # Docker 빌드
├── docker-compose.yml     # Docker Compose
├── .env.example           # 환경변수 예시
├── README.md              # 문서
├── LICENSE                # MIT 라이선스
└── tests/
    └── test_geo_fetch.py  # 테스트
```

---

## 구현 체크리스트

### Phase 1: MVP (beopsuny용)

- [ ] `geo_fetch.py` 핵심 기능 구현
  - [ ] GET /fetch 엔드포인트
  - [ ] GET /health 엔드포인트
  - [ ] 기본 에러 핸들링
  - [ ] 로깅
- [ ] Dockerfile 작성
- [ ] docker-compose.yml 작성
- [ ] README.md 작성
- [ ] GitHub 저장소 생성 (`sungjunlee/geo-fetch`)
- [ ] Synology/Portainer 배포 테스트
- [ ] Cloudflare Tunnel 연동
- [ ] beopsuny proxy_utils.py 수정

### Phase 2: 보안 및 안정성

- [ ] API 키 인증
- [ ] 도메인 화이트리스트/블랙리스트
- [ ] Rate limiting
- [ ] 요청/응답 로깅
- [ ] 에러 응답 개선

### Phase 3: 확장

- [ ] Docker Hub 게시
- [ ] POST 요청 지원
- [ ] 커스텀 헤더 전달
- [ ] JSON 응답 형식
- [ ] 바이너리 응답 지원
- [ ] 캐싱 (선택)
- [ ] 메트릭스 (Prometheus)

### Phase 4: 다국가 확장 (선택)

- [ ] 일본 인스턴스 (jp.geo-fetch.io)
- [ ] 미국 인스턴스 (us.geo-fetch.io)
- [ ] 중앙 라우터 (geo-fetch.io)

---

## 예상 코드 크기

| 파일 | 예상 라인 수 |
|------|-------------|
| `geo_fetch.py` | 150-200줄 |
| `Dockerfile` | 20줄 |
| `docker-compose.yml` | 25줄 |
| `README.md` | 200줄 |
| **총합** | ~400줄 |

---

## 배포 환경

### 초기 (beopsuny 전용)

```
[Synology NAS]
├── Docker Container: geo-fetch
├── Port: 8080 (내부)
└── Cloudflare Tunnel: kr.geo-fetch.jsonda.com → localhost:8080
```

### 향후 (범용)

```
[Oracle Cloud Free Tier - 춘천]
├── Docker Container: geo-fetch
├── Port: 80/443
├── 도메인: kr.geo-fetch.io
└── SSL: Cloudflare 또는 Let's Encrypt
```

---

## 테스트 시나리오

### 1. 기본 fetch 테스트

```bash
# 성공 케이스
curl "http://localhost:8080/fetch?url=http://httpbin.org/ip"
# 기대: {"origin": "121.x.x.x"} (한국 IP)

# 한국 정부 API
curl "http://localhost:8080/fetch?url=http://www.law.go.kr/DRF/lawSearch.do?OC=test&target=law&type=XML&query=민법"
# 기대: XML 응답 (법령 검색 결과)
```

### 2. 에러 케이스

```bash
# URL 없음
curl "http://localhost:8080/fetch"
# 기대: 400 Bad Request

# 잘못된 URL
curl "http://localhost:8080/fetch?url=not-a-url"
# 기대: 400 Bad Request

# 타임아웃
curl "http://localhost:8080/fetch?url=http://httpbin.org/delay/60&timeout=5"
# 기대: 504 Gateway Timeout

# 차단된 도메인 (ALLOWED_DOMAINS 설정 시)
curl "http://localhost:8080/fetch?url=http://google.com"
# 기대: 403 Forbidden
```

### 3. 인증 테스트

```bash
# API 키 없이 (API_KEY 설정 시)
curl "http://localhost:8080/fetch?url=http://example.com"
# 기대: 401 Unauthorized

# API 키 포함
curl -H "X-API-Key: correct-key" "http://localhost:8080/fetch?url=http://example.com"
# 기대: 200 OK
```

---

## 참고 자료

### 유사 프로젝트
- [CORS Anywhere](https://github.com/Rob--W/cors-anywhere) - CORS 프록시
- [AllOrigins](https://github.com/gnuns/allorigins) - CORS 프록시
- [Scrapoxy](https://scrapoxy.io/) - 프록시 풀 매니저

### 기술 문서
- [Python http.server](https://docs.python.org/3/library/http.server.html)
- [urllib.request](https://docs.python.org/3/library/urllib.request.html)
- [Docker Alpine Python](https://hub.docker.com/_/python)

### 관련 이슈
- Claude Code Web 샌드박스 제약 (DNS/소켓 차단)
- Cloudflare Tunnel CONNECT 메서드 차단
- 한국 정부 API 해외 IP 차단

---

## 새 세션 작업 시작 방법

```
다음과 같이 Claude에게 요청:

"geo-fetch 프로젝트를 만들려고 합니다.

GEO_FETCH_SPEC.md 스펙 문서를 참고해서:
1. sungjunlee/geo-fetch GitHub 저장소 생성
2. Phase 1 (MVP) 구현
3. Synology Docker에 배포 테스트

스펙 문서 위치: /Users/sjlee/workspace/active/legal-stack/beopsuny/proxy-wrapper/GEO_FETCH_SPEC.md"
```

---

## 변경 이력

| 날짜 | 버전 | 변경 내용 |
|------|------|----------|
| 2025-12-06 | 0.1.0 | 초기 스펙 작성 |
