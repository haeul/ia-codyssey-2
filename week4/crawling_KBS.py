import os
import sys
import time
from typing import List, Optional

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def setup_driver(chromedriver_path: Optional[str] = None, headless: bool = False) -> webdriver.Chrome:
    """크롬 드라이버를 초기화한다."""
    opts = Options()
    opts.add_argument('--lang=ko-KR')
    opts.add_argument('--window-size=1280,900')
    if headless:
        opts.add_argument('--headless=new')
        opts.add_argument('--disable-gpu')
    if chromedriver_path and os.path.exists(chromedriver_path):
        driver = webdriver.Chrome(options=opts)
    else:
        # PATH에 등록되어 있거나 Selenium이 자동탐색 가능한 경우
        driver = webdriver.Chrome(options=opts)
    driver.implicitly_wait(2)
    return driver


def wait_for(driver: webdriver.Chrome, by: By, value: str, timeout: int = 10):
    """지정 요소가 나타날 때까지 대기한다."""
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))


def login_naver(driver: webdriver.Chrome, user_id: str, user_pw: str) -> bool:
    """네이버에 로그인한다. 보안단계가 있으면 사용자 수동 입력을 허용한다."""
    driver.get('https://nid.naver.com/nidlogin.login')
    try:
        # 기본 입력창 대기
        wait_for(driver, By.CSS_SELECTOR, 'input[name="id"]', timeout=10)
    except TimeoutException:
        pass

    # 아이디/비번 입력 시도
    try:
        id_box = driver.find_element(By.CSS_SELECTOR, 'input[name="id"]')
        pw_box = driver.find_element(By.CSS_SELECTOR, 'input[name="pw"]')
        id_box.clear()
        id_box.send_keys(user_id)
        pw_box.clear()
        pw_box.send_keys(user_pw)

        # 로그인 버튼 클릭
        # 신규 UI/기존 UI 모두 커버 가능한 선택자 조합
        try:
            login_btn = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        except NoSuchElementException:
            login_btn = driver.find_element(By.ID, 'log.login')
        login_btn.click()
    except NoSuchElementException:
        # 로그인 화면 레이아웃이 변했거나, 보안단계로 바로 전환된 경우
        pass

    # 로그인 성공 판별: 메인으로 리다이렉트 + 로그인 쿠키 존재/상단 프로필 메뉴 노출
    # 보안문자/2단계 인증이 걸리면 사용자가 직접 완료할 때까지 대기
    success = False
    max_wait_sec = 120
    start = time.time()
    while time.time() - start < max_wait_sec:
        cur = driver.current_url
        # 메인으로 넘어갔거나, mail/naverpay 등 서비스 도메인으로 진입하면 성공으로 간주
        if 'https://www.naver.com/' in cur or 'mail.naver.com' in cur or 'news.naver.com' in cur:
            success = True
            break
        # 상단 우측 사용자 메뉴 등장 여부 체크(레이아웃 변동 대응해 폭넓게 탐색)
        els = driver.find_elements(By.CSS_SELECTOR, '[data-clk*="my"], a#NM_MY_ACCOUNT, a#gnb_my_page, a#account')
        if els:
            success = True
            break
        time.sleep(1)

    return success


def collect_mainpage_titles(driver: webdriver.Chrome, limit: int = 10) -> List[str]:
    """
    네이버 메인에서 노출되는 주요 타이틀 일부를 모은다.
    로그인 전/후 비교용으로 같은 함수로 수집해 리스트를 반환한다.
    """
    driver.get('https://www.naver.com/')
    time.sleep(2)

    candidates: List[str] = []

    # 뉴스/연예/스포츠 박스 등 다양한 블록에서 a 텍스트를 가져온다.
    # 메인 구조가 자주 바뀌므로 다중 셀렉터로 보수적으로 수집 후 정제한다.
    selectors = [
        'a.media_end_head_headline',                 # 뉴스 상세(가끔 메인 카드가 이 셀렉터를 씀)
        'div.section a',                             # 섹션 전반
        'a[href*="news.naver.com"]',                 # 뉴스 링크
        'a[href*="entertain.naver.com"]',            # 연예
        'a[href*="sports.naver.com"]',               # 스포츠
        'a.theme_item',                              # 테마 카드
        'strong.title, span.title, em.title',        # 제목 태그들
    ]

    seen = set()
    for css in selectors:
        for a in driver.find_elements(By.CSS_SELECTOR, css):
            txt = (a.text or '').strip()
            if txt and txt not in seen:
                seen.add(txt)
                candidates.append(txt)
            if len(candidates) >= limit:
                break
        if len(candidates) >= limit:
            break

    return candidates


def collect_mail_subjects(driver: webdriver.Chrome, limit: int = 30) -> List[str]:
    """
    로그인 사용자만 접근 가능한 네이버 메일함에서 최근 메일 제목을 수집한다.
    메일 UI가 자주 바뀌므로 여러 후보 셀렉터를 시도한다.
    """
    driver.get('https://mail.naver.com/')
    # 메일 리스트 로딩 대기(iframe/SPA 대비해서 넉넉히)
    time.sleep(4)

    subjects: List[str] = []
    tried_selectors = [
        'strong.mail_title',                             # 구형/일부 레이아웃
        'span.mail_title',                               # 변형
        'a.subject',                                     # 자주 쓰이는 클래스
        'div.subject a',                                 # 컨테이너 안 링크
        '[data-subject]',                                # 데이터 속성 보유
        '[role="row"] [role="gridcell"] a',              # ARIA 그리드 구조
    ]

    seen = set()
    for css in tried_selectors:
        for el in driver.find_elements(By.CSS_SELECTOR, css):
            text = (el.text or '').strip()
            if not text:
                # 일부는 title 속성에 제목이 담김
                text = (el.get_attribute('title') or '').strip()
            if text and text not in seen:
                seen.add(text)
                subjects.append(text)
            if len(subjects) >= limit:
                break
        if len(subjects) >= limit:
            break

    return subjects


def print_list(title: str, items: List[str]) -> None:
    """리스트를 보기 좋게 출력한다."""
    print('-' * 80)
    print(title)
    print('-' * 80)
    if not items:
        print('(데이터 없음)')
        return
    for i, v in enumerate(items, 1):
        print(f'{i:02d}. {v}')


def main() -> None:
    """엔트리 포인트."""
    # 환경변수 또는 입력 프롬프트로 계정 정보를 받는다.
    user_id = os.environ.get('NAVER_ID') or input('NAVER_ID 입력: ').strip()
    user_pw = os.environ.get('NAVER_PW') or input('NAVER_PW 입력: ').strip()

    # 필요 시 드라이버 경로 직접 지정 가능
    chromedriver_path = os.environ.get('CHROMEDRIVER_PATH')

    driver = setup_driver(chromedriver_path=chromedriver_path, headless=False)

    try:
        # 1) 로그인 전 메인 타이틀 샘플
        before_titles = collect_mainpage_titles(driver, limit=10)

        # 2) 로그인
        ok = login_naver(driver, user_id, user_pw)
        if not ok:
            print('로그인에 실패했습니다. 보안문자/2단계 인증을 완료했는지 확인하세요.')
            sys.exit(1)

        # 3) 로그인 후 메인 타이틀 샘플
        after_titles = collect_mainpage_titles(driver, limit=10)

        # 4) (로그인 전/후) 콘텐츠 차이 확인
        print_list('로그인 전 메인 타이틀', before_titles)
        print_list('로그인 후 메인 타이틀', after_titles)

        # 5) 로그인 사용자만 볼 수 있는 콘텐츠(사전 선정: 네이버 메일 제목들) 수집
        mail_subjects = collect_mail_subjects(driver, limit=30)
        print_list('네이버 메일 최근 제목', mail_subjects)

        # 6) 과제 요구: 리스트 객체에 담아서 화면에 출력 → 이미 리스트 형태로 수집/출력됨

    finally:
        # 화면 확인 시간을 조금 준 뒤 종료
        time.sleep(2)
        driver.quit()


if __name__ == '__main__':
    main()
