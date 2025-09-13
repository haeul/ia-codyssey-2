#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import threading


class ChatServer:
    """간단한 멀티스레드 채팅 서버."""

    def __init__(self, host: str = '0.0.0.0', port: int = 5000) -> None:
        self.host = host
        self.port = port
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # accept()가 영원히 막히지 않도록 타임아웃
        self.server_sock.settimeout(1.0)

        # 접속자 관리
        self.clients = {}   # {sock: nickname}
        self.nick_map = {}  # {nickname: sock}
        self.lock = threading.Lock()

        # 종료 플래그
        self.stop_event = threading.Event()

    def start(self) -> None:
        self.server_sock.bind((self.host, self.port))
        self.server_sock.listen()
        print(f'[*] 서버 시작: {self.host}:{self.port}')

        try:
            while not self.stop_event.is_set():
                try:
                    client_sock, addr = self.server_sock.accept()
                except socket.timeout:
                    # 주기적으로 깨어나 종료 플래그 확인
                    continue

                threading.Thread(
                    target=self._handle_client,
                    args=(client_sock, addr),
                    daemon=True,
                ).start()
        except KeyboardInterrupt:
            print('\n[*] Ctrl+C 감지: 서버 종료 중...')
        finally:
            self._shutdown()

    def _handle_client(self, client_sock: socket.socket, addr) -> None:
        try:
            nickname = self._handshake_for_nickname(client_sock)
            if nickname is None:
                client_sock.close()
                return

            self._register_client(client_sock, nickname)
            self._broadcast(f'[{nickname}]님이 입장하셨습니다.')

            self._send_line(client_sock, '안내: 일반 메시지는 모두에게 전송됩니다.')
            self._send_line(client_sock, '안내: 종료는 /종료, 귓속말은 /w 대상닉 메시지')

            while True:
                data = client_sock.recv(1024)
                if not data:
                    break

                msg = data.decode('utf-8', errors='ignore').strip()
                if not msg:
                    continue

                if msg == '/종료':
                    self._send_line(client_sock, '연결을 종료합니다.')
                    break

                if msg.startswith('/w '):
                    self._handle_whisper(client_sock, msg)
                    continue

                sender = self._get_nickname(client_sock)
                if sender is None:
                    break
                self._broadcast(f'{sender}> {msg}')
        except ConnectionResetError:
            pass
        finally:
            self._remove_client(client_sock)

    def _handshake_for_nickname(self, client_sock: socket.socket) -> str | None:
        self._send_line(client_sock, '닉네임을 입력해주세요:')
        try:
            data = client_sock.recv(1024)
        except ConnectionResetError:
            return None

        if not data:
            return None

        raw = data.decode('utf-8', errors='ignore').strip()
        if not raw:
            raw = 'user'

        nickname = self._make_unique_nickname(raw)
        self._send_line(client_sock, f'닉네임이 [{nickname}]로 설정되었습니다.')
        return nickname

    def _make_unique_nickname(self, base: str) -> str:
        with self.lock:
            if base not in self.nick_map:
                return base
            i = 2
            while True:
                cand = f'{base}{i}'
                if cand not in self.nick_map:
                    return cand
                i += 1

    def _register_client(self, client_sock: socket.socket, nickname: str) -> None:
        with self.lock:
            self.clients[client_sock] = nickname
            self.nick_map[nickname] = client_sock
        print(f'[*] 접속: {nickname}')

    def _remove_client(self, client_sock: socket.socket) -> None:
        with self.lock:
            nickname = self.clients.pop(client_sock, None)
            if nickname:
                self.nick_map.pop(nickname, None)
        if nickname:
            print(f'[*] 종료: {nickname}')
            self._broadcast(f'[{nickname}]님이 퇴장하셨습니다.')
        try:
            client_sock.close()
        except OSError:
            pass

    def _broadcast(self, line: str) -> None:
        with self.lock:
            targets = list(self.clients.keys())
        for sock in targets:
            self._send_line(sock, line)

    def _handle_whisper(self, sender_sock: socket.socket, raw_cmd: str) -> None:
        parts = raw_cmd.split(' ', 2)
        if len(parts) < 3:
            self._send_line(sender_sock, '형식: /w 대상닉 메시지')
            return

        _, target_nick, message = parts
        if not target_nick or not message:
            self._send_line(sender_sock, '형식: /w 대상닉 메시지')
            return

        with self.lock:
            target_sock = self.nick_map.get(target_nick)

        sender_nick = self._get_nickname(sender_sock) or '알수없음'

        if target_sock is None:
            self._send_line(sender_sock, f'대상 [{target_nick}]을(를) 찾을 수 없습니다.')
            return

        self._send_line(target_sock, f'(귓속말) {sender_nick}> {message}')
        self._send_line(sender_sock, f'(귓속말 전송) {sender_nick} -> {target_nick}: {message}')

    def _get_nickname(self, client_sock: socket.socket) -> str | None:
        with self.lock:
            return self.clients.get(client_sock)

    @staticmethod
    def _send_line(sock: socket.socket, line: str) -> None:
        try:
            data = (line + '\n').encode('utf-8')
            sock.sendall(data)
        except OSError:
            pass

    def _shutdown(self) -> None:
        """모든 클라이언트에 종료 안내 → 소켓 정리 → 서버 소켓 닫기."""
        self.stop_event.set()
        with self.lock:
            targets = list(self.clients.keys())
        for sock in targets:
            try:
                self._send_line(sock, '서버가 종료됩니다.')
                sock.close()
            except OSError:
                pass
        try:
            self.server_sock.close()
        except OSError:
            pass


def admin_console(server: ChatServer) -> None:
    """서버 콘솔에서 '/종료' 입력으로 안전 종료."""
    while True:
        try:
            cmd = input()
        except EOFError:
            break
        if cmd.strip() == '/종료':
            print('[*] 서버 종료 명령 수신')
            server._shutdown()
            break


def main() -> None:
    server = ChatServer(host='0.0.0.0', port=5000)
    # 관리 콘솔 스레드 시작
    threading.Thread(target=admin_console, args=(server,), daemon=True).start()
    # 서버 루프 시작
    server.start()


if __name__ == '__main__':
    main()
