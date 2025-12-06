# HTTP Proxy Wrapper for Cloudflare Tunnel

Cloudflare Tunnel은 HTTP 프록시 CONNECT 메서드를 차단하므로, 일반 HTTP 요청을 받아서 Synology Proxy로 포워딩하는 래퍼 서비스입니다.

## 구조

```
[Claude Code Web] → [beopsuny-proxy.jsonda.com]
    → [Cloudflare Tunnel]
    → [Proxy Wrapper:3129]
    → [Synology Proxy:3128]
    → [law.go.kr]
```

## Portainer 배포

### 1. 파일 업로드

Synology NAS에 폴더 생성:
```bash
mkdir -p /volume1/docker/beopsuny-proxy-wrapper
```

다음 파일들을 `/volume1/docker/beopsuny-proxy-wrapper/`에 업로드:
- `proxy_wrapper.py`
- `docker-compose.yml`

### 2. Portainer에서 Stack 추가

**Stacks** → **Add stack**

**Name**: `beopsuny-proxy-wrapper`

**Upload** 탭 선택 → `docker-compose.yml` 업로드

또는 **Web editor**에 `docker-compose.yml` 내용 붙여넣기

**Deploy the stack** 클릭

### 3. Cloudflare Tunnel Public Hostname 업데이트

기존 `proxy` hostname 수정:

| 항목 | 값 |
|------|-----|
| Subdomain | `proxy` |
| Domain | `jsonda.com` |
| Type | `HTTP` |
| URL | `localhost:3129` ← **변경** |

### 4. 테스트

로컬에서:
```bash
curl -x http://beopsuny-proxy.jsonda.com http://www.google.com
```

## 환경변수

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `UPSTREAM_PROXY` | 업스트림 프록시 주소 | `localhost:3128` |
| `PROXY_USER` | Synology Proxy 사용자명 | - |
| `PROXY_PASS` | Synology Proxy 비밀번호 | - |
| `PORT` | 래퍼 서비스 포트 | `3129` |

## 로그 확인

Portainer에서:
**Containers** → `beopsuny-proxy-wrapper` → **Logs**

## 문제 해결

### 1. "Connection refused"
- Synology Proxy가 3128 포트로 실행 중인지 확인
- `network_mode: host` 설정 확인

### 2. "407 Proxy Authentication Required"
- `PROXY_USER`, `PROXY_PASS` 환경변수 확인
- Synology Proxy 설정에서 인증 확인

### 3. "502 Bad Gateway"
- Synology Proxy가 응답하지 않음
- Synology Proxy 로그 확인
