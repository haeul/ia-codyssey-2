# main.py
from fastapi import FastAPI

from domain.question.router import router as question_router
from models import Base
from database import engine

app = FastAPI()

# 개발 초기에 create_all을 써도 되지만,
# 과제 요구사항에서는 Alembic으로 테이블을 생성하므로
# 아래 코드는 주석 처리해두고 설명용으로만 둔다.
# Base.metadata.create_all(bind=engine)

app.include_router(question_router)


@app.get('/')
def root() -> dict:
    return {'message': 'Simple Q&A board with SQLite and SQLAlchemy'}
