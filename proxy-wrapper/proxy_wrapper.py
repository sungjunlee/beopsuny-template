#!/usr/bin/env python3
"""
HTTP Proxy Wrapper for Cloudflare Tunnel

Cloudflare Tunnel은 HTTP 프록시 CONNECT 메서드를 차단합니다.
이 래퍼는 일반 HTTP 요청을 받아서 Synology Proxy(3128)로 포워딩합니다.

Usage:
    python proxy_wrapper.py

Environment:
    UPSTREAM_PROXY: 업스트림 프록시 (기본: localhost:3128)
    PROXY_USER: 프록시 인증 사용자명
    PROXY_PASS: 프록시 인증 비밀번호
    PORT: 서비스 포트 (기본: 3129)
"""

import base64
import os
import socket
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional


class ProxyWrapperHandler(BaseHTTPRequestHandler):
    """HTTP 요청을 업스트림 프록시로 포워딩"""

    # 업스트림 프록시 설정
    UPSTREAM_PROXY = os.environ.get("UPSTREAM_PROXY", "localhost:3128")
    PROXY_USER = os.environ.get("PROXY_USER", "")
    PROXY_PASS = os.environ.get("PROXY_PASS", "")

    def do_GET(self):
        """GET 요청 처리"""
        self._forward_request()

    def do_POST(self):
        """POST 요청 처리"""
        self._forward_request()

    def do_HEAD(self):
        """HEAD 요청 처리"""
        self._forward_request()

    def _forward_request(self):
        """요청을 업스트림 프록시로 포워딩"""
        try:
            # 요청 URL 파싱
            url = self.path
            if not url.startswith("http"):
                self.send_error(400, "Invalid URL - must start with http:// or https://")
                return

            # 업스트림 프록시 설정
            proxy_url = f"http://{self.UPSTREAM_PROXY}"
            if self.PROXY_USER and self.PROXY_PASS:
                proxy_url = f"http://{self.PROXY_USER}:{self.PROXY_PASS}@{self.UPSTREAM_PROXY}"

            proxy_handler = urllib.request.ProxyHandler({
                "http": proxy_url,
                "https": proxy_url,
            })
            opener = urllib.request.build_opener(proxy_handler)

            # 요청 헤더 복사
            headers = {}
            for key, value in self.headers.items():
                # Hop-by-hop 헤더 제외
                if key.lower() not in ("connection", "proxy-connection", "keep-alive",
                                       "proxy-authenticate", "proxy-authorization",
                                       "te", "trailers", "transfer-encoding", "upgrade"):
                    headers[key] = value

            # 요청 본문 읽기 (POST 등)
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length) if content_length > 0 else None

            # 업스트림 프록시로 요청
            req = urllib.request.Request(url, data=body, headers=headers, method=self.command)

            with opener.open(req, timeout=30) as response:
                # 응답 상태 코드
                self.send_response(response.status)

                # 응답 헤더 복사
                for key, value in response.headers.items():
                    if key.lower() not in ("connection", "keep-alive", "proxy-connection",
                                           "transfer-encoding"):
                        self.send_header(key, value)

                self.end_headers()

                # 응답 본문
                self.wfile.write(response.read())

        except urllib.error.HTTPError as e:
            self.send_error(e.code, str(e.reason))
        except urllib.error.URLError as e:
            self.send_error(502, f"Bad Gateway: {e.reason}")
        except socket.timeout:
            self.send_error(504, "Gateway Timeout")
        except Exception as e:
            self.send_error(500, f"Internal Server Error: {str(e)}")

    def log_message(self, format, *args):
        """로그 메시지 (stdout)"""
        print(f"{self.address_string()} - [{self.log_date_time_string()}] {format % args}")


def main():
    port = int(os.environ.get("PORT", "3129"))
    upstream = os.environ.get("UPSTREAM_PROXY", "localhost:3128")

    print("=" * 60)
    print("HTTP Proxy Wrapper for Cloudflare Tunnel")
    print("=" * 60)
    print(f"Listening on: 0.0.0.0:{port}")
    print(f"Upstream proxy: {upstream}")
    print(f"Authentication: {'Enabled' if os.environ.get('PROXY_USER') else 'Disabled'}")
    print("=" * 60)
    print()

    server = HTTPServer(("0.0.0.0", port), ProxyWrapperHandler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
