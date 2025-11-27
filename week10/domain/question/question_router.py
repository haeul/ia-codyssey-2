# domain/question/question_router.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import Question

router = APIRouter(
    prefix='/api/question',
    tags=['question'],
)


@router.get('/list')
def question_list(db: Session = Depends(get_db)):
    """질문 목록을 반환하는 API."""
    questions = db.query(Question).order_by(Question.id.desc()).all()

    # ORM 객체를 그대로 리턴하면 직렬화가 애매하니, dict 리스트로 변환
    result = []
    for question in questions:
        result.append(
            {
                'id': question.id,
                'subject': question.subject,
                'content': question.content,
                'create_date': question.create_date,
            }
        )
    return result
