# cloudflared-proxy-wrapper 프로젝트 작업 지시서

## 프로젝트 개요

### 목적
Cloudflare Tunnel을 통해 HTTP 프록시를 안전하게 외부에 노출하기 위한 래퍼 서비스

### 배경 문제
1. **Cloudflare Tunnel의 제약**: HTTP 프록시의 CONNECT 메서드를 보안상 차단함
2. **기존 프록시 활용**: Synology NAS의 Squid 프록시(3128 포트) 등 기존 HTTP 프록시를 외부에서 사용하고 싶음
3. **DNS/방화벽 제약**: 홈 DDNS(`*.asuscomm.com`)는 기업 방화벽이나 Claude Code Web 등에서 차단됨

### 해결 방안
일반 HTTP GET/POST 요청을 받아서 업스트림 프록시(Squid)로 포워딩하는 경량 래퍼 서비스

```
[클라이언트] → [proxy.jsonda.com (Cloudflare Tunnel)]
    → [Proxy Wrapper:3129 (Docker)]
    → [Squid:3128 (Synology)]
    → [목적지 서버]
```

## 기술 스택

- **언어**: Python 3.11 (표준 라이브러리만 사용, 의존성 없음)
- **배포**: Docker (Portainer Stack으로 관리)
- **프록시**: Synology Squid / 기타 HTTP 프록시

## 프로젝트 구조

```
cloudflared-proxy-wrapper/
├── proxy_wrapper.py          # 메인 프록시 래퍼 서비스
├── docker-compose.yml        # Docker Compose 설정
├── .env.example              # 환경변수 예시
├── README.md                 # 사용자 문서
├── LICENSE                   # MIT 라이선스
└── .gitignore
```

## 핵심 파일 설명

### 1. proxy_wrapper.py

**역할**: HTTP 요청을 받아 업스트림 프록시로 포워딩

**주요 기능**:
- HTTP GET/POST/HEAD 메서드 지원
- 프록시 인증 (Basic Auth) 지원
- 요청/응답 헤더 투명 전달 (Hop-by-hop 헤더 제외)
- 타임아웃, 에러 처리
- 상세 로깅

**환경변수**:
- `UPSTREAM_PROXY`: 업스트림 프록시 (기본: `localhost:3128`)
- `PROXY_USER`: 프록시 인증 사용자명 (선택)
- `PROXY_PASS`: 프록시 인증 비밀번호 (선택)
- `PORT`: 래퍼 서비스 포트 (기본: `3129`)

**기술 세부사항**:
- `http.server.HTTPServer` 사용
- `urllib.request.ProxyHandler`로 업스트림 프록시 연결
- Hop-by-hop 헤더 필터링 (RFC 2616 준수)

### 2. docker-compose.yml

**역할**: Docker 배포 설정

**주요 설정**:
```yaml
services:
  proxy-wrapper:
    image: python:3.11-slim
    network_mode: host  # 로컬 Squid 접근 위해
    ports:
      - "3129:3129"
    environment:
      - UPSTREAM_PROXY=localhost:3128
      - PROXY_USER=proxyuser
      - PROXY_PASS=proxy.chulnas
    volumes:
      - ./proxy_wrapper.py:/app/proxy_wrapper.py:ro
    command: python -u proxy_wrapper.py
    restart: always
```

**주의사항**:
- `network_mode: host` 필수 (Synology 내 다른 컨테이너/서비스 접근)
- `volumes`는 **읽기 전용**(`:ro`) 권장
- `-u` 옵션으로 Python 버퍼링 비활성화 (로그 실시간 출력)

### 3. README.md

**포함 내용**:
1. **프로젝트 소개**: 왜 필요한지, 어떻게 작동하는지
2. **사용 사례**: Synology + Cloudflare Tunnel 조합
3. **Quick Start**:
   - 일반 Docker Compose 사용법
   - Portainer Stack 사용법
4. **Cloudflare Tunnel 설정**:
   - Tunnel 생성 가이드
   - Public Hostname 설정 (`localhost:3129`)
5. **환경변수 설명**
6. **테스트 방법**:
   ```bash
   curl -x http://proxy.jsonda.com http://www.google.com
   ```
7. **문제 해결**:
   - Connection refused
   - 407 Proxy Authentication Required
   - 502 Bad Gateway
8. **보안 고려사항**:
   - 프록시 인증 필수 권장
   - Cloudflare Access 추가 보안
   - 방화벽 설정

### 4. .env.example

```env
# 업스트림 프록시 설정
UPSTREAM_PROXY=localhost:3128

# 프록시 인증 (선택)
PROXY_USER=your_username
PROXY_PASS=your_password

# 서비스 포트
PORT=3129
```

## 배포 시나리오

### 시나리오 1: Portainer (Synology NAS)

1. GitHub 공개 저장소 생성: `sungjunlee/cloudflared-proxy-wrapper`
2. Portainer → Stacks → Add stack
3. Repository 탭:
   - URL: `https://github.com/sungjunlee/cloudflared-proxy-wrapper`
   - Compose path: `docker-compose.yml`
4. Environment variables 설정
5. Deploy

### 시나리오 2: 일반 Docker Compose

```bash
git clone https://github.com/sungjunlee/cloudflared-proxy-wrapper.git
cd cloudflared-proxy-wrapper
cp .env.example .env
# .env 파일 수정
docker-compose up -d
```

### 시나리오 3: Standalone Docker

```bash
docker run -d \
  --name proxy-wrapper \
  --network host \
  -e UPSTREAM_PROXY=localhost:3128 \
  -e PROXY_USER=proxyuser \
  -e PROXY_PASS=password \
  -e PORT=3129 \
  -v $(pwd)/proxy_wrapper.py:/app/proxy_wrapper.py:ro \
  -w /app \
  python:3.11-slim \
  python -u proxy_wrapper.py
```

## Cloudflare Tunnel 설정

### 1. Tunnel 생성

```bash
# Portainer에 cloudflared 컨테이너 배포
# 또는 Cloudflare Zero Trust 대시보드에서 생성
```

### 2. Public Hostname 설정

| 항목 | 값 |
|------|-----|
| Subdomain | `proxy` |
| Domain | `jsonda.com` |
| Type | `HTTP` |
| URL | `localhost:3129` |

결과: `https://proxy.jsonda.com` → Proxy Wrapper

## 사용 예시 (beopsuny 프로젝트)

### 환경변수 설정

```bash
export BEOPSUNY_PROXY_TYPE=http
export BEOPSUNY_PROXY_URL='http://proxy.jsonda.com'
```

### settings.yaml 설정

```yaml
proxy:
  type: "http"
  url: "http://proxy.jsonda.com"
```

### 테스트

```bash
# Python 스크립트에서 자동 사용
python .claude/skills/beopsuny/scripts/fetch_law.py search "민법" --type law
```

## 작업 체크리스트

### 필수 작업

- [ ] GitHub 공개 저장소 생성 (`cloudflared-proxy-wrapper`)
- [ ] `proxy_wrapper.py` 코드 정리 및 주석 추가
- [ ] `docker-compose.yml` 최종 검토
- [ ] `.env.example` 생성
- [ ] `README.md` 작성:
  - [ ] 프로젝트 소개
  - [ ] 아키텍처 다이어그램
  - [ ] Quick Start
  - [ ] Cloudflare Tunnel 설정 가이드
  - [ ] 환경변수 설명
  - [ ] 테스트 방법
  - [ ] 문제 해결
  - [ ] 보안 가이드
- [ ] `LICENSE` 파일 추가 (MIT)
- [ ] `.gitignore` 생성 (`.env`, `__pycache__/`)

### 선택 작업

- [ ] GitHub Actions CI/CD (Docker 이미지 빌드)
- [ ] 사전 빌드된 Docker 이미지 제공 (Docker Hub / GHCR)
- [ ] 다중 프록시 지원 (라운드 로빈)
- [ ] 헬스체크 엔드포인트 (`/health`)
- [ ] 메트릭스 (Prometheus 형식)

## 기술 제약사항

### Cloudflare Tunnel 제약

- **CONNECT 메서드 차단**: HTTP 터널링 불가
- **웹소켓 제한**: 별도 설정 필요
- **타임아웃**: 100초 (idle connection)

### 해결책

- GET/POST 방식으로 우회 (현재 구현)
- 요청을 완전히 프록시로 포워딩하여 투명성 유지

## 보안 고려사항

### 1. 프록시 인증 필수

```yaml
environment:
  - PROXY_USER=strong_username
  - PROXY_PASS=strong_password_here
```

### 2. Cloudflare Access (선택)

Cloudflare Zero Trust에서 Access Policy 추가:
- Email 기반 인증
- IP 화이트리스트

### 3. 로그 모니터링

```bash
# Portainer에서 로그 확인
# 비정상 요청 패턴 감지
```

## 테스트 시나리오

### 1. 기본 연결 테스트

```bash
curl -v -x http://proxy.jsonda.com http://www.google.com
```

**기대 결과**: 200 OK, Google HTML

### 2. 한국 정부 API 테스트 (beopsuny)

```bash
curl -x http://proxy.jsonda.com "http://www.law.go.kr/DRF/lawSearch.do?OC=sungjunlee.kr&target=law&type=XML&query=민법"
```

**기대 결과**: XML 응답 (법령 검색 결과)

### 3. HTTPS 테스트

```bash
curl -x http://proxy.jsonda.com https://www.google.com
```

**기대 결과**: 200 OK (Squid가 HTTPS 처리)

### 4. 프록시 인증 테스트

업스트림 프록시에 인증 설정 후:

```bash
# 인증 없이 요청 → 407 기대
curl -x http://proxy.jsonda.com http://www.google.com

# Wrapper가 자동으로 업스트림 인증 처리 → 200 기대
```

### 5. 에러 처리 테스트

```bash
# 존재하지 않는 도메인
curl -x http://proxy.jsonda.com http://nonexistent.invalid

# 타임아웃 (응답 느린 서버)
curl -x http://proxy.jsonda.com http://httpbin.org/delay/60
```

## 참고 자료

### Cloudflare Tunnel 문서
- https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/
- https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/routing-to-tunnel/

### HTTP 프록시 스펙
- RFC 2616: HTTP/1.1
- RFC 7230: HTTP/1.1 Message Syntax and Routing

### Squid 프록시
- http://www.squid-cache.org/Doc/

## 기존 파일 위치

현재 `beopsuny` 프로젝트의 `proxy-wrapper/` 폴더에 초안 파일 존재:
- `/Users/sjlee/workspace/active/legal-stack/beopsuny/proxy-wrapper/proxy_wrapper.py`
- `/Users/sjlee/workspace/active/legal-stack/beopsuny/proxy-wrapper/docker-compose.yml`
- `/Users/sjlee/workspace/active/legal-stack/beopsuny/proxy-wrapper/README.md`

이 파일들을 새 저장소로 이동하고 다듬어야 함.

## 예상 작업 시간

- 저장소 생성 및 초기 설정: 10분
- README.md 작성: 30분
- 코드 정리 및 주석: 20분
- 테스트 및 검증: 20분
- **총 예상 시간**: 1시간 30분

## 성공 기준

1. ✅ GitHub 공개 저장소 생성 완료
2. ✅ Portainer에서 배포 성공
3. ✅ `curl -x http://proxy.jsonda.com http://www.google.com` 성공
4. ✅ beopsuny 프로젝트에서 한국 정부 API 접근 성공
5. ✅ README.md가 초보자도 따라할 수 있을 정도로 상세함

## 향후 개선 사항

- Docker Hub에 공식 이미지 게시
- Helm Chart (Kubernetes 지원)
- SOCKS5 프록시 지원 추가
- Access 로그 구조화 (JSON)
- Rate limiting 기능

---

## 새 세션에서 작업 시작 방법

```
Claude에게 다음과 같이 요청:

"cloudflared-proxy-wrapper 프로젝트를 새로 만들려고 합니다.
현재 /Users/sjlee/workspace/active/legal-stack/beopsuny/proxy-wrapper/에
초안 파일들이 있습니다.

이 파일들을 기반으로 sungjunlee/cloudflared-proxy-wrapper 공개 저장소를
만들고 싶습니다. PROJECT_BRIEF.md를 참고해서 작업해주세요."
```
