# main.py
from fastapi import FastAPI

from database import init_db
from question_router import router as question_router


def create_app() -> FastAPI:
    app = FastAPI()

    # 라우터 등록
    app.include_router(question_router)

    # 앱 시작 시 DB 초기화
    @app.on_event('startup')
    def on_startup() -> None:
        init_db()

    return app


app = create_app()
