# database.py
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

SQLALCHEMY_DATABASE_URL = 'sqlite:///./app.db'

# SQLite + FastAPI에서 권장되는 설정
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={'check_same_thread': False},
)

SessionLocal = sessionmaker(
    autocommit=False,   # 과제 요구사항
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
