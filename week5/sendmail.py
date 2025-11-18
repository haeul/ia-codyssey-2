"""
sendmail.py
- 표준 라이브러리만 사용한 Gmail SMTP 메일 발송 스크립트
- SSL(465) 또는 STARTTLS(587) 지원
- 본문 텍스트, 첨부파일 전송, 상세 예외 처리 포함
- PEP 8 규칙과 과제 코딩 스타일 가이드 준수
"""

import argparse
import getpass
import mimetypes
import os
import socket
import ssl
import sys
from email.message import EmailMessage
from pathlib import Path
from smtplib import (
    SMTP,
    SMTP_SSL,
    SMTPAuthenticationError,
    SMTPConnectError,
    SMTPDataError,
    SMTPException,
    SMTPRecipientsRefused,
    SMTPSenderRefused,
    SMTPServerDisconnected,
)

GMAIL_SMTP_HOST = 'smtp.gmail.com'
DEFAULT_SSL_PORT = 465
DEFAULT_STARTTLS_PORT = 587


def build_message(sender: str, to: list, subject: str, body: str) -> EmailMessage:
    """
    메일 메시지 객체를 생성한다.
    """
    msg = EmailMessage()
    msg['From'] = sender
    msg['To'] = ', '.join(to)
    msg['Subject'] = subject
    msg.set_content(body or '')
    return msg


def attach_files(msg: EmailMessage, file_paths: list) -> None:
    """
    첨부파일 경로 리스트를 받아 메시지에 첨부한다.
    존재하지 않는 파일은 건너뛰되, 사용자에게 경고를 출력한다.
    """
    for fp in file_paths:
        path = Path(fp).expanduser()
        if not path.is_file():
            print(f'[경고] 첨부 불가(파일 없음): {path}', file=sys.stderr)
            continue

        ctype, encoding = mimetypes.guess_type(path.name)
        if ctype is None or encoding is not None:
            ctype = 'application/octet-stream'

        maintype, subtype = ctype.split('/', 1)
        with path.open('rb') as f:
            data = f.read()

        msg.add_attachment(
            data,
            maintype=maintype,
            subtype=subtype,
            filename=path.name,
        )


def send_via_ssl(host: str, port: int, user: str, password: str, msg: EmailMessage) -> None:
    """
    SSL 포트(일반적으로 465)로 직접 TLS 연결 후 전송.
    """
    context = ssl.create_default_context()
    with SMTP_SSL(host=host, port=port, context=context, timeout=30) as server:
        server.login(user=user, password=password)
        server.send_message(msg)


def send_via_starttls(host: str, port: int, user: str, password: str, msg: EmailMessage) -> None:
    """
    평문 연결 후 STARTTLS(일반적으로 587)로 TLS 업그레이드 후 전송.
    """
    with SMTP(host=host, port=port, timeout=30) as server:
        server.ehlo()
        server.starttls(context=ssl.create_default_context())
        server.ehlo()
        server.login(user=user, password=password)
        server.send_message(msg)


def safe_send(
    use_ssl: bool,
    host: str,
    port: int,
    user: str,
    password: str,
    msg: EmailMessage,
) -> bool:
    """
    전송을 수행하고 발생 가능한 예외를 처리한다.
    성공 시 True, 실패 시 False를 반환한다.
    """
    try:
        if use_ssl:
            send_via_ssl(host=host, port=port, user=user, password=password, msg=msg)
        else:
            send_via_starttls(host=host, port=port, user=user, password=password, msg=msg)
        print('[정보] 메일 전송 성공')
        return True

    except SMTPAuthenticationError as e:
        print('[에러] 인증 실패: 앱 비밀번호를 사용했는지, 계정/비밀번호가 올바른지 확인하세요.', file=sys.stderr)
        print(f'       코드={e.smtp_code}, 메시지={e.smtp_error!r}', file=sys.stderr)
    except SMTPConnectError as e:
        print('[에러] SMTP 서버 연결 실패', file=sys.stderr)
        print(f'       코드={e.smtp_code}, 메시지={e.smtp_error!r}', file=sys.stderr)
    except SMTPRecipientsRefused as e:
        print('[에러] 수신자 주소 거부', file=sys.stderr)
        print(f'       거부 목록={e.recipients}', file=sys.stderr)
    except SMTPSenderRefused as e:
        print('[에러] 발신자 주소 거부', file=sys.stderr)
        print(f'       코드={e.smtp_code}, 메시지={e.smtp_error!r}, 발신자={e.sender}', file=sys.stderr)
    except SMTPDataError as e:
        print('[에러] 데이터 전송 실패', file=sys.stderr)
        print(f'       코드={e.smtp_code}, 메시지={e.smtp_error!r}', file=sys.stderr)
    except SMTPServerDisconnected:
        print('[에러] 서버 연결이 예기치 않게 종료됨', file=sys.stderr)
    except (socket.gaierror, TimeoutError):
        print('[에러] 네트워크 오류: 호스트명, 포트, 방화벽 설정을 확인하세요.', file=sys.stderr)
    except FileNotFoundError as e:
        print('[에러] 첨부 파일을 찾을 수 없음', file=sys.stderr)
        print(f'       파일={e.filename}', file=sys.stderr)
    except SMTPException as e:
        print('[에러] 일반 SMTP 예외 발생', file=sys.stderr)
        print(f'       상세={e}', file=sys.stderr)
    except Exception as e:
        print('[에러] 알 수 없는 예외 발생', file=sys.stderr)
        print(f'       상세={e}', file=sys.stderr)

    return False


def parse_args(argv: list) -> argparse.Namespace:
    """
    명령행 인자를 파싱한다.
    """
    parser = argparse.ArgumentParser(
        description='Gmail SMTP 메일 발송 (표준 라이브러리 전용)'
    )

    parser.add_argument('--sender', required=False, help='보내는 Gmail 주소')
    parser.add_argument('--password', required=False, help='앱 비밀번호 (미지정 시 프롬프트 입력)')
    parser.add_argument('--to', required=True, nargs='+', help='받는 사람 이메일 주소(공백으로 다수 지정)')
    parser.add_argument('--subject', required=True, help='메일 제목')
    parser.add_argument('--body', required=False, default='', help='메일 본문 텍스트')
    parser.add_argument('--attach', required=False, nargs='*', default=[], help='첨부 파일 경로들')
    parser.add_argument('--host', required=False, default=GMAIL_SMTP_HOST, help='SMTP 호스트명')
    parser.add_argument('--port', required=False, type=int, help='SMTP 포트 (465 SSL / 587 STARTTLS)')
    parser.add_argument('--ssl', action='store_true', help='SSL 모드 사용 (기본은 STARTTLS)')
    return parser.parse_args(argv)


def main(argv: list) -> int:
    """
    프로그램 진입점.
    """
    args = parse_args(argv)

    sender = args.sender or os.environ.get('GMAIL_SENDER', '')
    if not sender:
        sender = input('보내는 Gmail 주소를 입력하세요: ').strip()

    password = args.password or os.environ.get('GMAIL_APP_PASSWORD', '')
    if not password:
        password = getpass.getpass('앱 비밀번호를 입력하세요: ').strip()

    if args.ssl:
        port = args.port or DEFAULT_SSL_PORT
    else:
        port = args.port or DEFAULT_STARTTLS_PORT

    msg = build_message(sender=sender, to=args.to, subject=args.subject, body=args.body)

    if args.attach:
        attach_files(msg, args.attach)

    ok = safe_send(
        use_ssl=args.ssl,
        host=args.host,
        port=port,
        user=sender,
        password=password,
        msg=msg,
    )
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
