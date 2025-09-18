#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen
from urllib.error import URLError
from datetime import datetime
import socket
import os
import json


HOST = '0.0.0.0'
PORT = 8080
INDEX_FILE = 'index.html'
ENABLE_GEOLOOKUP = True  # 보너스 기능: IP → 위치 조회 (표준 라이브러리로 외부 API 호출)


def is_private_ip(ip: str) -> bool:
    """사설/로컬 IP 여부."""
    try:
        packed = socket.inet_aton(ip)
        b0 = packed[0]
        b1 = packed[1]
        # 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.0/8
        return (
            b0 == 10
            or (b0 == 172 and 16 <= b1 <= 31)
            or (b0 == 192 and b1 == 168)
            or b0 == 127
        )
    except OSError:
        return ip in ('::1',)  # IPv6 loopback


def geo_lookup(ip: str) -> str:
    """외부 API(ip-api.com)로 간단 위치 조회. 실패 시 빈 문자열."""
    if not ENABLE_GEOLOOKUP or is_private_ip(ip):
        return ''
    url = f'http://ip-api.com/json/{ip}?fields=status,country,regionName,city,query'
    try:
        with urlopen(url, timeout=2.0) as resp:
            data = json.loads(resp.read().decode('utf-8', errors='ignore'))
        if data.get('status') == 'success':
            country = data.get('country') or ''
            region = data.get('regionName') or ''
            city = data.get('city') or ''
            return f'{country} {region} {city}'.strip()
    except (URLError, TimeoutError, ValueError):
        pass
    return ''


class SimpleHandler(BaseHTTPRequestHandler):
    """index.html을 제공하는 간단 HTTP 핸들러."""

    def do_GET(self) -> None:  # noqa: N802 (과제 규칙에선 snake_case 허용)
        # 접속 정보 출력
        ip = self.client_address[0]
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        location = geo_lookup(ip)
        loc_msg = f' | 위치: {location}' if location else ''
        print(f'[접속] 시간: {ts} | IP: {ip}{loc_msg}')

        # 라우팅: / 또는 /index.html 만 처리
        if self.path in ('/', '/index.html'):
            self._serve_index()
        else:
            self._send_not_found()

    # ---- 내부 헬퍼 ----
    def _serve_index(self) -> None:
        if not os.path.exists(INDEX_FILE):
            body = (
                '<!doctype html><meta charset="utf-8">'
                '<h1>index.html 이 없습니다.</h1>'
            ).encode('utf-8')
            self._send_response(200, 'text/html; charset=utf-8', body)
            return

        with open(INDEX_FILE, 'rb') as f:
            body = f.read()
        self._send_response(200, 'text/html; charset=utf-8', body)

    def _send_not_found(self) -> None:
        body = (
            '<!doctype html><meta charset="utf-8">'
            '<h1>404 Not Found</h1>'
        ).encode('utf-8')
        self._send_response(404, 'text/html; charset=utf-8', body)

    def _send_response(self, code: int, content_type: str, body: bytes) -> None:
        self.send_response(code)  # 여기서 200/404 등 상태코드 헤더 전송
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # 기본 로그(한 줄) 대신 우리가 이미 print로 찍으니 조용히 처리
    def log_message(self, fmt: str, *args) -> None:  # noqa: D401
        return


def run_server() -> None:
    server = HTTPServer((HOST, PORT), SimpleHandler)
    print(f'[*] HTTP 서버 시작: http://{HOST}:{PORT}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n[*] 종료 중...')
    finally:
        server.server_close()
        print('[*] 서버 종료')


if __name__ == '__main__':
    run_server()
