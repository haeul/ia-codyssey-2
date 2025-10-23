#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
import getpass
import re
import smtplib
import ssl
from typing import List, Tuple, Dict
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


SMTP_PROFILES: Dict[str, Dict[str, str]] = {
    # STARTTLS on 587
    'gmail': {
        'host': 'smtp.gmail.com',
        'port': 587,
        'hint': 'Gmail은 계정 보안을 위해 앱 비밀번호 사용을 권장합니다.'
    },
    'naver': {
        'host': 'smtp.naver.com',
        'port': 587,
        'hint': '네이버는 SMTP 사용 시 POP3/IMAP 사용 설정이 켜져 있어야 합니다.'
    }
}


def is_valid_email(addr: str) -> bool:
    """아주 간단한 이메일 형식 검사 (RFC 완전 준수 아님)."""
    pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
    return bool(re.match(pattern, addr.strip()))


def load_targets(csv_path: str) -> List[Tuple[str, str]]:
    """CSV에서 (이름, 이메일) 목록을 읽어 유효한 이메일만 반환한다."""
    targets: List[Tuple[str, str]] = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get('이름') or '').strip()
            email = (row.get('이메일') or '').strip()
            if name and email and is_valid_email(email):
                targets.append((name, email))
    # 중복 이메일 제거 (마지막 항목 우선)
    unique: Dict[str, str] = {e: n for (n, e) in targets}
    return [(n, e) for e, n in unique.items()]


def build_message_html(sender_email: str,
                       sender_name: str,
                       to_addrs: List[str],
                       subject: str,
                       html_body: str,
                       text_body: str) -> MIMEMultipart:
    """HTML + Plain 멀티파트 메시지를 생성한다."""
    msg = MIMEMultipart('alternative')
    msg['From'] = f'{sender_name} <{sender_email}>'
    msg['To'] = ', '.join(to_addrs)
    msg['Subject'] = subject

    part_text = MIMEText(text_body, 'plain', 'utf-8')
    part_html = MIMEText(html_body, 'html', 'utf-8')

    msg.attach(part_text)
    msg.attach(part_html)
    return msg


def render_bulk_bodies() -> Tuple[str, str]:
    """다중 수신자용(개인화 없음) 본문을 반환한다."""
    text = (
        '안녕하세요.\n'
        '과제 공지 드립니다.\n'
        '- 과제1: HTML 메일 발송\n'
        '- CSV에서 수신자 읽기\n'
        '자세한 내용은 첨부 본문(HTML)을 확인해주세요.'
    )
    html = (
        '<!doctype html>'
        '<html><body>'
        '<h2>안녕하세요.</h2>'
        '<p>과제 공지 드립니다.</p>'
        '<ul>'
        '<li>과제1: <b>HTML 메일 발송</b></li>'
        '<li>CSV에서 수신자 읽기</li>'
        '</ul>'
        '<p>성실한 수행 부탁드립니다.</p>'
        '</body></html>'
    )
    return html, text


def render_individual_bodies(name: str) -> Tuple[str, str]:
    """개별 수신자용(이름 개인화) 본문을 반환한다."""
    safe_name = name.replace('<', '').replace('>', '')
    text = (
        f'{safe_name}님 안녕하세요.\n'
        '아래 과제 공지 전달드립니다.\n'
        '- 과제1: HTML 메일 발송\n'
        '- CSV에서 수신자 읽기\n'
        '궁금한 점은 회신 부탁드립니다.'
    )
    html = (
        '<!doctype html>'
        '<html><body>'
        f'<h2>{safe_name}님 안녕하세요.</h2>'
        '<p>아래 과제 공지를 전달드립니다.</p>'
        '<ol>'
        '<li><b>HTML 메일 발송</b></li>'
        '<li>CSV에서 수신자 읽기</li>'
        '</ol>'
        '<p>궁금한 점은 이 메일로 회신해주세요.</p>'
        '</body></html>'
    )
    return html, text


def send_bulk(smtp_host: string, smtp_port: int,
              account: str, password: str,
              sender_name: str, subject: str,
              targets: List[Tuple[str, str]]) -> None:
    """여러 명을 한 번에 TO에 넣어 한 통의 메일로 발송."""
    to_list = [email for _, email in targets]
    html, text = render_bulk_bodies()
    message = build_message_html(
        sender_email=account,
        sender_name=sender_name,
        to_addrs=to_list,
        subject=subject,
        html_body=html,
        text_body=text
    )

    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(account, password)
        server.sendmail(account, to_list, message.as_string())


def send_individual(smtp_host: string, smtp_port: int,
                    account: str, password: str,
                    sender_name: str, subject: str,
                    targets: List[Tuple[str, str]]) -> None:
    """수신자별로 한 통씩 개별 발송(이름 개인화)."""
    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(account, password)

        for name, email in targets:
            html, text = render_individual_bodies(name)
            message = build_message_html(
                sender_email=account,
                sender_name=sender_name,
                to_addrs=[email],
                subject=subject,
                html_body=html,
                text_body=text
            )
            server.sendmail(account, [email], message.as_string())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='CSV 기반 HTML 메일 발송 스크립트 (표준 라이브러리만 사용)'
    )
    parser.add_argument('--provider', choices=SMTP_PROFILES.keys(), required=True,
                        help='smtp 프로바이더 선택: gmail | naver')
    parser.add_argument('--mode', choices=['bulk', 'individual'], required=True,
                        help='bulk=여러 명에게 한 번에 / individual=개별 발송')
    parser.add_argument('--csv', required=True, help='수신자 CSV 경로 (헤더: 이름,이메일)')
    parser.add_argument('--subject', required=True, help='메일 제목')
    parser.add_argument('--from-name', required=True, help='보내는 사람 표시 이름')
    parser.add_argument('--account', help='SMTP 로그인 계정 이메일(미지정 시 provider 기준 안내)')
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    profile = SMTP_PROFILES[args.provider]
    smtp_host = profile['host']
    smtp_port = profile['port']

    account = args.account
    if not account:
        print(f"[안내] --account 미지정. {args.provider} 계정 이메일을 입력하세요.")
        account = input('SMTP 계정 이메일: ').strip()

    print(f"[힌트] {profile['hint']}")
    password = getpass.getpass('SMTP 앱 비밀번호/계정 비밀번호 입력: ')

    targets = load_targets(args.csv)
    if not targets:
        print('수신 대상이 없습니다. CSV 내용을 확인하세요.')
        return

    try:
        if args.mode == 'bulk':
            send_bulk(
                smtp_host=smtp_host,
                smtp_port=smtp_port,
                account=account,
                password=password,
                sender_name=args.from_name,
                subject=args.subject,
                targets=targets
            )
            print(f'완료: {len(targets)}명에게 한 통으로 일괄 발송했습니다.')
        else:
            send_individual(
                smtp_host=smtp_host,
                smtp_port=smtp_port,
                account=account,
                password=password,
                sender_name=args.from_name,
                subject=args.subject,
                targets=targets
            )
            print(f'완료: {len(targets)}명에게 개별 발송했습니다.')
    except smtplib.SMTPAuthenticationError:
        print('인증 실패: 계정/비밀번호(앱 비밀번호) 또는 2단계 보안 설정을 확인하세요.')
    except smtplib.SMTPRecipientsRefused:
        print('수신자가 거부되었습니다. 이메일 주소를 확인하세요.')
    except Exception as exc:
        print(f'오류 발생: {exc}')


if __name__ == '__main__':
    main()
