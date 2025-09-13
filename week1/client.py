#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import threading
import sys


def recv_worker(sock: socket.socket) -> None:
    """서버 수신 전용 스레드."""
    try:
        while True:
            data = sock.recv(1024)
            if not data:
                print('[연결 종료됨]')
                break
            msg = data.decode('utf-8', errors='ignore')
            print(msg, end='')  # 서버가 줄바꿈 포함 전송
    except OSError:
        pass
    finally:
        try:
            sock.close()
        except OSError:
            pass


def main() -> None:
    host = '127.0.0.1'
    port = 5000

    if len(sys.argv) == 3:
        host = sys.argv[1]
        port = int(sys.argv[2])

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))

    t = threading.Thread(target=recv_worker, args=(sock,), daemon=True)
    t.start()

    try:
        while True:
            text = input()
            if not text:
                continue
            sock.sendall((text + '\n').encode('utf-8'))
            if text == '/종료':
                break
    except (KeyboardInterrupt, EOFError):
        try:
            sock.sendall(('/종료\n').encode('utf-8'))
        except OSError:
            pass
    finally:
        try:
            sock.close()
        except OSError:
            pass


if __name__ == '__main__':
    main()
