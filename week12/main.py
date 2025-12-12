# main.py
from fastapi import FastAPI

from database import Base, engine
from models import Question
from question_router import router as question_router

app = FastAPI()

# 테이블 생성
Base.metadata.create_all(bind = engine)

# 라우터 등록
app.include_router(question_router)
