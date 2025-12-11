# database.py
import sqlite3
from contextlib import contextmanager
from typing import Iterator

DB_PATH = 'question.db'


def init_db() -> None:
    '''애플리케이션 시작 시 한 번만 호출해서 테이블 생성.'''
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute(
            '''
            create table if not exists question (
                id integer primary key autoincrement,
                subject text not null,
                content text not null
            )
            '''
        )
        conn.commit()
    finally:
        conn.close()


@contextmanager
def db_session() -> Iterator[sqlite3.Connection]:
    '''
    contextlib.contextmanager를 사용한 DB 세션 컨텍스트.

    with db_session() as conn:
        ...
    이런 식으로 쓰면, 블록이 끝날 때 자동으로 conn.close()가 호출된다.
    '''
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def get_db() -> Iterator[sqlite3.Connection]:
    '''
    FastAPI Depends에서 사용할 의존성 함수.

    - 내부에서 contextlib 기반 db_session()을 사용
    - yield를 사용한 "generator dependency" 이기 때문에
      요청이 끝난 후 FastAPI가 자동으로 정리 구간을 실행한다.
    '''
    with db_session() as conn:
        yield conn
