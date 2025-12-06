# Feature Request: URL Encoding Layer for Cloudflare WAF Bypass

## 요약

cors-anywhere-gateway에 URL 난독화 레이어를 추가하여 Cloudflare WAF의 Open Proxy 패턴 탐지를 회피합니다.

## 배경

### 문제 상황

Cloudflare Tunnel을 통해 cors-anywhere를 노출할 때, Cloudflare WAF가 다음 패턴을 탐지하여 차단할 수 있습니다:

```
https://gateway.example.com/http://target.com/api
                           ↑
                    URL 경로에 http:// 포함 → SSRF/Open Proxy로 판단
```

### 증상

- 간헐적 502 Bad Gateway
- 일부 요청만 성공, 일부는 차단
- Cloudflare Security Events에 차단 로그

## 제안하는 해결책

### URL 인코딩 엔드포인트 추가

기존 방식과 새로운 방식을 모두 지원:

| 엔드포인트 | 형식 | 용도 |
|-----------|------|------|
| `/{url}` | 기존 cors-anywhere 호환 | 직접 노출 시 |
| `/fetch/{encoded}` | Base64URL 인코딩 | Cloudflare 경유 시 |

### 요청 흐름

```
[클라이언트]
    │
    │ GET /fetch/aHR0cDovL3d3dy5sYXcuZ28ua3IvRFJGLy4uLg
    ▼
[Cloudflare WAF] → 일반 API 요청으로 인식, 통과
    │
    ▼
[cors-anywhere-gateway]
    │ Base64URL 디코딩 → http://www.law.go.kr/DRF/...
    ▼
[Target Server]
```

## 구현 명세

### 1. 새로운 엔드포인트

```
GET /fetch/{encodedUrl}
```

**파라미터:**
- `encodedUrl`: Base64URL 인코딩된 전체 URL

**예시:**
```bash
# 원본 URL
http://www.law.go.kr/DRF/lawSearch.do?OC=test&target=law&type=XML&query=민법

# Base64URL 인코딩
aHR0cDovL3d3dy5sYXcuZ28ua3IvRFJGL2xhd1NlYXJjaC5kbz9PQz10ZXN0JnRhcmdldD1sYXcmdHlwZT1YTUwmcXVlcnk9656L67KV

# 요청
GET /fetch/aHR0cDovL3d3dy5sYXcuZ28ua3IvRFJGL2xhd1NlYXJjaC5kbz9PQz10ZXN0JnRhcmdldD1sYXcmdHlwZT1YTUwmcXVlcnk9656L67KV
```

### 2. 인코딩 방식: Base64URL

- 표준 Base64가 아닌 **Base64URL** 사용 (RFC 4648)
- URL-safe 문자만 사용: `A-Z`, `a-z`, `0-9`, `-`, `_`
- 패딩(`=`) 생략 가능

**이유:**
- URL 경로에 안전하게 포함 가능
- 추가 URL 인코딩 불필요
- 대부분의 언어에서 기본 지원

### 3. 서버 측 구현 (TypeScript)

```typescript
// src/routes/fetch.ts
import type { IncomingMessage, ServerResponse } from 'node:http';

/**
 * Base64URL 디코딩
 */
function decodeBase64Url(encoded: string): string {
  // Base64URL → Base64 변환
  let base64 = encoded
    .replace(/-/g, '+')
    .replace(/_/g, '/');

  // 패딩 추가
  const padding = base64.length % 4;
  if (padding) {
    base64 += '='.repeat(4 - padding);
  }

  return Buffer.from(base64, 'base64').toString('utf8');
}

/**
 * /fetch/:encoded 엔드포인트 핸들러
 */
export function handleFetchRoute(
  req: IncomingMessage,
  res: ServerResponse,
  encodedUrl: string
): string | null {
  try {
    const decodedUrl = decodeBase64Url(encodedUrl);

    // URL 유효성 검사
    if (!decodedUrl.startsWith('http://') && !decodedUrl.startsWith('https://')) {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Invalid URL: must start with http:// or https://' }));
      return null;
    }

    return decodedUrl;  // cors-anywhere로 전달할 URL 반환
  } catch (e) {
    res.writeHead(400, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Invalid Base64URL encoding' }));
    return null;
  }
}
```

### 4. 클라이언트 측 구현 (Python)

```python
import base64

def encode_url_for_gateway(url: str) -> str:
    """URL을 Base64URL로 인코딩"""
    return base64.urlsafe_b64encode(url.encode()).decode().rstrip('=')

def decode_url_from_gateway(encoded: str) -> str:
    """Base64URL에서 URL 디코딩"""
    # 패딩 복원
    padding = 4 - len(encoded) % 4
    if padding != 4:
        encoded += '=' * padding
    return base64.urlsafe_b64decode(encoded).decode()

# 사용 예시
original_url = "http://www.law.go.kr/DRF/lawSearch.do?OC=test&target=law&type=XML&query=민법"
encoded = encode_url_for_gateway(original_url)
# → aHR0cDovL3d3dy5sYXcuZ28ua3IvRFJGL2xhd1NlYXJjaC5kbz9PQz10ZXN0JnRhcmdldD1sYXcmdHlwZT1YTUwmcXVlcnk9656L67KV

gateway_url = f"https://gateway.example.com/fetch/{encoded}"
```

### 5. 클라이언트 측 구현 (JavaScript/TypeScript)

```typescript
function encodeUrlForGateway(url: string): string {
  return btoa(url)
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}

function decodeUrlFromGateway(encoded: string): string {
  let base64 = encoded
    .replace(/-/g, '+')
    .replace(/_/g, '/');

  const padding = base64.length % 4;
  if (padding) {
    base64 += '='.repeat(4 - padding);
  }

  return atob(base64);
}

// 사용 예시
const originalUrl = "http://www.law.go.kr/DRF/lawSearch.do?query=민법";
const encoded = encodeUrlForGateway(originalUrl);
const gatewayUrl = `https://gateway.example.com/fetch/${encoded}`;
```

## 설정 옵션

### 환경변수

```bash
# 인코딩 엔드포인트 활성화 (기본: true)
ENABLE_ENCODED_ENDPOINT=true

# 기존 방식(/{url}) 비활성화 (Cloudflare 전용 시)
DISABLE_DIRECT_ENDPOINT=false
```

## 보안 고려사항

### 1. URL 유효성 검사

디코딩된 URL이 `http://` 또는 `https://`로 시작하는지 반드시 확인:

```typescript
if (!decodedUrl.match(/^https?:\/\//)) {
  throw new Error('Invalid URL scheme');
}
```

### 2. 도메인 허용 목록 (기존 기능 유지)

인코딩 여부와 관계없이 도메인 allowlist/blocklist 적용:

```typescript
const url = new URL(decodedUrl);
if (!isAllowedDomain(url.hostname)) {
  throw new Error('Domain not allowed');
}
```

### 3. 로깅

디코딩된 원본 URL을 로그에 기록하여 디버깅 지원:

```typescript
console.log(`[fetch] Encoded request: ${encodedUrl.substring(0, 20)}...`);
console.log(`[fetch] Decoded URL: ${decodedUrl}`);
```

## 테스트 케이스

### 1. 기본 인코딩/디코딩

```bash
# 인코딩 테스트
echo -n "http://example.com" | base64 | tr '+/' '-_' | tr -d '='
# → aHR0cDovL2V4YW1wbGUuY29t

# 요청 테스트
curl https://gateway.example.com/fetch/aHR0cDovL2V4YW1wbGUuY29t
```

### 2. 한글 포함 URL

```bash
# 원본: http://law.go.kr/api?query=민법
# 인코딩: aHR0cDovL2xhdy5nby5rci9hcGk_cXVlcnk9656L67KV
curl https://gateway.example.com/fetch/aHR0cDovL2xhdy5nby5rci9hcGk_cXVlcnk9656L67KV
```

### 3. 잘못된 인코딩

```bash
curl https://gateway.example.com/fetch/invalid!!!
# 기대: 400 Bad Request, {"error": "Invalid Base64URL encoding"}
```

### 4. 잘못된 URL 스킴

```bash
# file:// 스킴 시도
curl https://gateway.example.com/fetch/ZmlsZTovLy9ldGMvcGFzc3dk
# 기대: 400 Bad Request, {"error": "Invalid URL: must start with http:// or https://"}
```

## beopsuny 통합

### proxy_utils.py 업데이트

```python
import base64

def fetch_with_gateway(
    url: str,
    timeout: int = 30,
    headers: Optional[dict] = None,
    use_encoding: bool = True,  # 새로운 옵션
) -> str:
    config = get_gateway_config()
    gateway_url = config.get("url")

    if use_encoding:
        # Base64URL 인코딩 방식
        encoded = base64.urlsafe_b64encode(url.encode()).decode().rstrip('=')
        full_url = f"{gateway_url}/fetch/{encoded}"
    else:
        # 기존 방식
        full_url = f"{gateway_url}/{url}"

    # ... 나머지 동일
```

### 환경변수

```bash
# 인코딩 방식 사용 (기본: true)
BEOPSUNY_GATEWAY_USE_ENCODING=true
```

## 구현 우선순위

1. **Phase 1**: `/fetch/{encoded}` 엔드포인트 추가
2. **Phase 2**: 환경변수로 엔드포인트 on/off 설정
3. **Phase 3**: beopsuny proxy_utils.py 업데이트

## 참고

- [RFC 4648 - Base64URL](https://datatracker.ietf.org/doc/html/rfc4648#section-5)
- [Cloudflare WAF Managed Rules](https://developers.cloudflare.com/waf/managed-rules/)
- [OWASP SSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
