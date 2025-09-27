#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
crawling_KBS.py

- KBS(http://news.kbs.co.kr) 메인 페이지에서 '주요 헤드라인'을 수집하여 List로 출력
- BeautifulSoup 사용 (설치: pip install beautifulsoup4)
- requests 사용 (표준 허용)
- PEP 8 스타일 및 과제 제약 준수
- 문자열은 기본적으로 ' ' 사용
- 보너스: 네이버 금융에서 KOSPI 지수 간단 수집 예시 포함
"""

from typing import List, Optional
import sys
import time

import requests
from bs4 import BeautifulSoup


KBS_NEWS_URL = 'http://news.kbs.co.kr'
USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)

# 개발자 도구로 확인한 '고유 셀렉터'를 최상단에 배치하세요.
# 아래는 안전 장치를 위해 준비한 후보 셀렉터들입니다.
SELECTOR_CANDIDATES: List[str] = [
    # 예: 메인 헤드라인 영역 내부의 기사 링크(가정)
    'section[id*="headline"] a[href*="/news/"]',
    'div[id*="headline"] a[href*="/news/"]',
    # 리스트형 기사 타이틀(가정)
    'div.news_list a.tit',
    'ul li a[href*="/news/"]',
    # 일반적인 타이틀 링크 백업(가정)
    'h1 a[href*="/news/"]',
    'h2 a[href*="/news/"]',
    'h3 a[href*="/news/"]',
]


def fetch_html(url: str, timeout_sec: int = 10) -> Optional[str]:
    """URL 에서 HTML 문자열을 가져온다."""
    headers = {'User-Agent': USER_AGENT}
    try:
        res = requests.get(url, headers=headers, timeout=timeout_sec)
        res.raise_for_status()
        # 일부 사이트는 인코딩을 명시하지 않으므로, requests 추정 인코딩 사용
        res.encoding = res.apparent_encoding
        return res.text
    except requests.RequestException as exc:
        print(f'[ERROR] 요청 실패: {exc}', file=sys.stderr)
        return None


def normalize_text(s: str) -> str:
    """공백 정리용 유틸리티."""
    return ' '.join(s.split())


def parse_kbs_headlines(html: str, max_count: int = 15) -> List[str]:
    """
    BeautifulSoup을 사용하여 KBS 메인 페이지에서 헤드라인 텍스트를 추출한다.
    - 여러 CSS 셀렉터 후보를 순차적으로 시도
    - 처음 유효한 결과가 나오는 셀렉터를 사용
    """
    soup = BeautifulSoup(html, 'html.parser')

    # 스크립트/스타일 제거(안전)
    for tag in soup(['script', 'style', 'noscript']):
        tag.decompose()

    # 중복 방지를 위한 집합
    seen = set()
    headlines: List[str] = []

    for selector in SELECTOR_CANDIDATES:
        elements = soup.select(selector)
        texts = []

        for el in elements:
            # 링크 노드일 경우 a 태그 내부 텍스트 우선
            text = el.get_text(strip=True)
            text = normalize_text(text)
            if not text:
                continue
            # 메뉴/광고성/공백성 텍스트 등 간단 필터
            if len(text) < 3:
                continue
            # 중복 제거
            if text in seen:
                continue
            seen.add(text)
            texts.append(text)

        # 이 셀렉터에서 유의미한 텍스트를 수집했다면, 그것만 사용하고 종료
        if len(texts) >= 5:  # 최소 5개 이상이면 헤드라인 후보로 판단(가변 가능)
            headlines.extend(texts)
            break

    # 그래도 충분치 않으면 상위 일부만이라도 반환
    if not headlines:
        # 백업: 페이지 내 모든 a 태그에서 제목처럼 보이는 텍스트 수집
        for a in soup.find_all('a'):
            text = normalize_text(a.get_text(strip=True))
            if len(text) >= 5 and text not in seen:
                seen.add(text)
                headlines.append(text)

    # 최종 개수 제한
    return headlines[:max_count]


def print_headlines(headlines: List[str]) -> None:
    """헤드라인 리스트를 번호와 함께 출력한다."""
    if not headlines:
        print('[INFO] 헤드라인을 찾지 못했습니다. 셀렉터를 확인하세요.')
        return
    print('=== KBS 주요 헤드라인 ===')
    for i, title in enumerate(headlines, start=1):
        print(f'{i:02d}. {title}')


# ────────────────────────────── 보너스: 간단한 주가(코스피) 수집 ──────────────────────────────

NAVER_SISE_URL = 'https://finance.naver.com/sise/'


def fetch_kospi_index() -> Optional[str]:
    """네이버 금융에서 KOSPI 지수를 간단히 가져온다."""
    html = fetch_html(NAVER_SISE_URL)
    if html is None:
        return None
    soup = BeautifulSoup(html, 'html.parser')

    # 네이버 금융의 KOSPI 지수 영역 id는 통상 'KOSPI_now'
    node = soup.select_one('#KOSPI_now')
    if node and node.get_text(strip=True):
        return normalize_text(node.get_text(strip=True))

    # 백업: 대체 위치 탐색(사이트 개편 대비)
    alt = soup.find('span', id=lambda v: isinstance(v, str) and 'KOSPI' in v)
    if alt:
        return normalize_text(alt.get_text(strip=True))

    return None


def main() -> None:
    """엔트리 포인트."""
    start = time.time()
    html = fetch_html(KBS_NEWS_URL)
    if html is None:
        print('[ERROR] KBS 페이지를 불러오지 못했습니다.')
        sys.exit(1)

    headlines = parse_kbs_headlines(html, max_count=15)
    print_headlines(headlines)

    # 보너스: KOSPI 지수 한 줄 출력
    kospi = fetch_kospi_index()
    if kospi:
        print('\n=== 보너스: 현재 KOSPI 지수(네이버 금융) ===')
        print(f'KOSPI: {kospi}')

    elapsed = time.time() - start
    print(f'\n[INFO] 실행 시간: {elapsed:.2f}s')


if __name__ == '__main__':
    main()
