# cors-anywhere-gateway

CORS Anywhere를 래핑한 인증 지원 HTTP Fetch 게이트웨이

## 프로젝트 개요

### 목적
[cors-anywhere](https://github.com/Rob--W/cors-anywhere)를 기반으로 API 키 인증, Docker 패키징, 모던 TypeScript 스택을 추가한 프로덕션 레디 HTTP 게이트웨이

### 배경 문제
1. **CORS 제약**: 브라우저에서 외부 API 직접 호출 불가
2. **지역 제한 API**: 한국 정부 API 등 특정 지역에서만 접근 가능
3. **보안 필요**: 공개 프록시는 남용 위험

### 해결 방안
```
[클라이언트] → [cors-anywhere-gateway (한국 서버)]
    → [API 키 검증]
    → [cors-anywhere 코어]
    → [목적지 서버 (law.go.kr 등)]
```

## 기술 스택

| 항목 | 선택 | 이유 |
|------|------|------|
| **Runtime** | Node.js 20 LTS | 안정성, cors-anywhere 호환 |
| **Language** | TypeScript 5.x | 타입 안전성, 모던 개발 |
| **Core** | cors-anywhere | 10년+ 검증된 HTTP 프록시 |
| **Build** | esbuild | 빠른 번들링, 단일 파일 출력 |
| **Package Manager** | pnpm | 빠른 설치, 디스크 효율 |
| **Container** | Docker Alpine | 경량 이미지 (~50MB) |
| **Linter** | Biome | 빠른 lint + format 통합 |

## 프로젝트 구조

```
cors-anywhere-gateway/
├── src/
│   ├── index.ts              # 엔트리포인트
│   ├── server.ts             # 서버 설정 및 시작
│   ├── middleware/
│   │   ├── auth.ts           # API 키 인증
│   │   ├── rate-limit.ts     # Rate limiting (선택)
│   │   └── logging.ts        # 요청 로깅
│   ├── config.ts             # 환경변수 설정
│   └── types.ts              # 타입 정의
├── Dockerfile
├── docker-compose.yml
├── package.json
├── tsconfig.json
├── biome.json
├── .env.example
├── .gitignore
├── LICENSE                   # MIT
└── README.md
```

## 핵심 파일 설명

### 1. src/index.ts

```typescript
import { startServer } from './server';
import { config } from './config';

console.log('='.repeat(60));
console.log('cors-anywhere-gateway');
console.log('='.repeat(60));
console.log(`Port: ${config.port}`);
console.log(`Auth: ${config.apiKey ? 'Enabled' : 'Disabled'}`);
console.log('='.repeat(60));

startServer();
```

### 2. src/config.ts

```typescript
export const config = {
  port: parseInt(process.env.PORT || '8080', 10),
  apiKey: process.env.API_KEY || '',

  // cors-anywhere 옵션
  originWhitelist: process.env.ORIGIN_WHITELIST?.split(',') || [],
  originBlacklist: process.env.ORIGIN_BLACKLIST?.split(',') || [],

  // Rate limiting
  rateLimit: {
    maxRequests: parseInt(process.env.RATE_LIMIT_MAX || '100', 10),
    windowMs: parseInt(process.env.RATE_LIMIT_WINDOW || '60000', 10),
  },

  // 타임아웃 (ms)
  timeout: parseInt(process.env.TIMEOUT || '30000', 10),
} as const;

export type Config = typeof config;
```

### 3. src/server.ts

```typescript
import corsAnywhere from 'cors-anywhere';
import { config } from './config';
import { authMiddleware } from './middleware/auth';

export function startServer(): void {
  const server = corsAnywhere.createServer({
    originWhitelist: config.originWhitelist,
    originBlacklist: config.originBlacklist,

    // API 키 인증
    handleInitialRequest: authMiddleware,

    // 보안: 민감한 헤더 제거
    removeHeaders: ['cookie', 'cookie2', 'x-api-key'],

    // 리다이렉트 최적화
    redirectSameOrigin: true,

    // HTTPS 요청 시 인증서 검증
    httpProxyOptions: {
      xfwd: false,
    },
  });

  server.listen(config.port, '0.0.0.0', () => {
    console.log(`Server running on http://0.0.0.0:${config.port}`);
  });
}
```

### 4. src/middleware/auth.ts

```typescript
import type { IncomingMessage, ServerResponse } from 'node:http';
import { config } from '../config';

/**
 * API 키 인증 미들웨어
 * @returns true면 요청 처리 완료 (프록시 안함), false면 정상 진행
 */
export function authMiddleware(
  req: IncomingMessage,
  res: ServerResponse,
  _location: string
): boolean {
  // API 키가 설정되지 않았으면 인증 스킵
  if (!config.apiKey) {
    return false;
  }

  const providedKey = req.headers['x-api-key'];

  if (providedKey !== config.apiKey) {
    res.writeHead(401, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      error: 'Unauthorized',
      message: 'Invalid or missing API key',
    }));
    return true; // 요청 처리 완료
  }

  return false; // 정상 진행
}
```

### 5. src/middleware/logging.ts (선택)

```typescript
import type { IncomingMessage } from 'node:http';

export function logRequest(req: IncomingMessage, targetUrl: string): void {
  const timestamp = new Date().toISOString();
  const method = req.method || 'UNKNOWN';
  const clientIp = req.headers['x-forwarded-for'] || req.socket.remoteAddress;

  console.log(`[${timestamp}] ${method} ${targetUrl} - ${clientIp}`);
}
```

### 6. package.json

```json
{
  "name": "cors-anywhere-gateway",
  "version": "1.0.0",
  "description": "CORS Anywhere wrapper with API key auth and Docker support",
  "type": "module",
  "main": "dist/index.js",
  "scripts": {
    "dev": "tsx watch src/index.ts",
    "build": "esbuild src/index.ts --bundle --platform=node --target=node20 --outfile=dist/index.js --format=esm --packages=external",
    "start": "node dist/index.js",
    "lint": "biome check .",
    "lint:fix": "biome check --write .",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "cors-anywhere": "^0.4.4"
  },
  "devDependencies": {
    "@biomejs/biome": "^1.9.0",
    "@types/node": "^20.0.0",
    "esbuild": "^0.24.0",
    "tsx": "^4.19.0",
    "typescript": "^5.6.0"
  },
  "engines": {
    "node": ">=20.0.0"
  },
  "license": "MIT"
}
```

### 7. tsconfig.json

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "lib": ["ES2022"],
    "strict": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "resolveJsonModule": true,
    "declaration": true,
    "outDir": "dist",
    "rootDir": "src"
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

### 8. biome.json

```json
{
  "$schema": "https://biomejs.dev/schemas/1.9.0/schema.json",
  "organizeImports": {
    "enabled": true
  },
  "linter": {
    "enabled": true,
    "rules": {
      "recommended": true
    }
  },
  "formatter": {
    "enabled": true,
    "indentStyle": "space",
    "indentWidth": 2
  }
}
```

### 9. Dockerfile

```dockerfile
# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# pnpm 설치
RUN corepack enable && corepack prepare pnpm@latest --activate

# 의존성 설치
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# 소스 복사 및 빌드
COPY tsconfig.json biome.json ./
COPY src ./src
RUN pnpm run build

# Production stage
FROM node:20-alpine AS runner

WORKDIR /app

# 보안: non-root 사용자
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 gateway

# pnpm 설치
RUN corepack enable && corepack prepare pnpm@latest --activate

# 프로덕션 의존성만 설치
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --prod --frozen-lockfile

# 빌드 결과물 복사
COPY --from=builder /app/dist ./dist

USER gateway

EXPOSE 8080

CMD ["node", "dist/index.js"]
```

### 10. docker-compose.yml

```yaml
services:
  cors-anywhere-gateway:
    build: .
    container_name: cors-anywhere-gateway
    restart: always
    ports:
      - "8080:8080"
    environment:
      - PORT=8080
      - API_KEY=${CORS_GATEWAY_API_KEY:-}
      - ORIGIN_WHITELIST=${CORS_GATEWAY_ORIGIN_WHITELIST:-}
      - ORIGIN_BLACKLIST=${CORS_GATEWAY_ORIGIN_BLACKLIST:-}
      - RATE_LIMIT_MAX=${CORS_GATEWAY_RATE_LIMIT_MAX:-100}
      - RATE_LIMIT_WINDOW=${CORS_GATEWAY_RATE_LIMIT_WINDOW:-60000}
      - TIMEOUT=${CORS_GATEWAY_TIMEOUT:-30000}
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:8080/"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### 11. .env.example

```bash
# 서버 설정
PORT=8080

# 인증 (필수 권장)
API_KEY=your-secret-api-key-here

# Origin 제어 (쉼표 구분)
ORIGIN_WHITELIST=
ORIGIN_BLACKLIST=

# Rate Limiting
RATE_LIMIT_MAX=100
RATE_LIMIT_WINDOW=60000

# 타임아웃 (ms)
TIMEOUT=30000
```

### 12. .gitignore

```gitignore
node_modules/
dist/
.env
*.log
.DS_Store
```

## API 사용법

### 기본 사용

```bash
# API 키 없이 (API_KEY 미설정 시)
curl http://localhost:8080/http://example.com

# API 키 포함
curl -H "x-api-key: your-secret-key" \
  http://localhost:8080/http://law.go.kr/DRF/lawSearch.do?target=law&query=민법
```

### URL 형식

```
http://<gateway-host>:<port>/<target-url>

예시:
http://localhost:8080/http://www.google.com
http://localhost:8080/https://api.example.com/data
```

### 응답 헤더

cors-anywhere가 자동으로 추가하는 CORS 헤더:
- `Access-Control-Allow-Origin: *`
- `Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS`
- `Access-Control-Allow-Headers: *`

## 배포 시나리오

### 시나리오 1: Portainer (Synology NAS)

1. GitHub 저장소: `sungjunlee/cors-anywhere-gateway`
2. Portainer → Stacks → Add stack
3. Repository 탭:
   - URL: `https://github.com/sungjunlee/cors-anywhere-gateway`
   - Compose path: `docker-compose.yml`
4. Environment variables:
   - `CORS_GATEWAY_API_KEY`: 시크릿 키 설정
5. Deploy

### 시나리오 2: 로컬 Docker

```bash
git clone https://github.com/sungjunlee/cors-anywhere-gateway
cd cors-anywhere-gateway
cp .env.example .env
# .env 파일 수정

docker compose up -d
```

### 시나리오 3: 개발 모드

```bash
pnpm install
pnpm dev
```

## Cloudflare Tunnel 연동

### Public Hostname 설정

| 항목 | 값 |
|------|-----|
| Subdomain | `fetch-gateway` |
| Domain | `jsonda.com` |
| Type | `HTTP` |
| URL | `localhost:8080` |

결과: `https://fetch-gateway.jsonda.com` → cors-anywhere-gateway

## beopsuny 통합

### 환경변수

```bash
export BEOPSUNY_FETCH_GATEWAY=https://fetch-gateway.jsonda.com
export BEOPSUNY_FETCH_API_KEY=your-api-key
```

### Python 클라이언트 코드

```python
import os
import urllib.parse
import urllib.request

def fetch_via_gateway(url: str) -> bytes:
    """게이트웨이를 통해 URL fetch"""
    gateway = os.environ.get('BEOPSUNY_FETCH_GATEWAY', '')
    api_key = os.environ.get('BEOPSUNY_FETCH_API_KEY', '')

    if not gateway:
        # 게이트웨이 없으면 직접 요청
        with urllib.request.urlopen(url, timeout=30) as response:
            return response.read()

    # 게이트웨이 URL 구성
    fetch_url = f"{gateway}/{url}"

    # 요청 생성
    req = urllib.request.Request(fetch_url)
    if api_key:
        req.add_header('x-api-key', api_key)

    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read()


# 사용 예시
if __name__ == '__main__':
    url = 'http://www.law.go.kr/DRF/lawSearch.do?OC=test&target=law&type=XML&query=민법'
    data = fetch_via_gateway(url)
    print(data.decode('utf-8'))
```

## 테스트 시나리오

### 1. 기본 연결 테스트

```bash
curl -H "x-api-key: your-key" \
  http://localhost:8080/http://www.google.com
```

**기대 결과**: 200 OK, Google HTML

### 2. API 키 없이 요청

```bash
curl http://localhost:8080/http://www.google.com
```

**기대 결과**: 401 Unauthorized (API_KEY 설정 시)

### 3. 한국 정부 API 테스트

```bash
curl -H "x-api-key: your-key" \
  "http://localhost:8080/http://www.law.go.kr/DRF/lawSearch.do?OC=test&target=law&type=XML&query=민법"
```

**기대 결과**: XML 응답 (법령 검색 결과)

### 4. HTTPS 테스트

```bash
curl -H "x-api-key: your-key" \
  http://localhost:8080/https://api.github.com
```

**기대 결과**: 200 OK, GitHub API 응답

## 구현 체크리스트

### Phase 1: 프로젝트 셋업
- [ ] GitHub 저장소 생성
- [ ] pnpm + TypeScript 초기화
- [ ] Biome 설정
- [ ] 기본 디렉토리 구조

### Phase 2: 코어 구현
- [ ] config.ts - 환경변수 설정
- [ ] server.ts - cors-anywhere 래핑
- [ ] middleware/auth.ts - API 키 인증
- [ ] index.ts - 엔트리포인트

### Phase 3: Docker화
- [ ] Dockerfile (멀티스테이지 빌드)
- [ ] docker-compose.yml
- [ ] .env.example

### Phase 4: 문서화
- [ ] README.md
- [ ] LICENSE (MIT)

### Phase 5: 배포 및 테스트
- [ ] Portainer 배포
- [ ] Cloudflare Tunnel 연동
- [ ] beopsuny 통합 테스트

## 보안 고려사항

### 1. API 키 필수

```bash
# 강력한 키 생성
openssl rand -hex 32
```

### 2. Cloudflare Access (선택)

Zero Trust 대시보드에서 추가 인증 레이어 설정 가능

### 3. Rate Limiting

환경변수로 설정:
```bash
RATE_LIMIT_MAX=100      # 윈도우당 최대 요청
RATE_LIMIT_WINDOW=60000 # 윈도우 크기 (ms)
```

### 4. 로그 모니터링

Portainer 또는 `docker logs`로 비정상 패턴 감지

## 향후 개선 사항

- [ ] Prometheus 메트릭 엔드포인트 (`/metrics`)
- [ ] 헬스체크 엔드포인트 개선 (`/health`)
- [ ] 도메인 allowlist/blocklist 기능
- [ ] 응답 캐싱 (선택적)
- [ ] Docker Hub 이미지 게시

## 참고 자료

- [cors-anywhere GitHub](https://github.com/Rob--W/cors-anywhere)
- [cors-anywhere 옵션 문서](https://github.com/Rob--W/cors-anywhere#documentation)
- [Cloudflare Tunnel 문서](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)

---

## 새 세션에서 작업 시작 방법

```
Claude에게 다음과 같이 요청:

"cors-anywhere-gateway 프로젝트를 만들려고 합니다.
CORS_ANYWHERE_GATEWAY_SPEC.md 스펙 문서를 참고해서 작업해주세요.

위치: /Users/sjlee/workspace/active/legal-stack/cors-anywhere-gateway
(또는 원하는 위치)"
```
