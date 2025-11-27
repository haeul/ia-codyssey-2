# domain/question/router.py
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import Question

router = APIRouter(
    prefix='/questions',
    tags=['questions'],
)


@router.get('/', response_model=List[dict])
def read_questions(db: Session = Depends(get_db)) -> List[dict]:
    questions = db.query(Question).order_by(Question.id.desc()).all()
    return [
        {
            'id': q.id,
            'subject': q.subject,
            'content': q.content,
            'create_date': q.create_date,
        }
        for q in questions
    ]


@router.post('/', response_model=dict)
def create_question(
    subject: str,
    content: str,
    db: Session = Depends(get_db),
) -> dict:
    question = Question(
        subject=subject,
        content=content,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return {
        'id': question.id,
        'subject': question.subject,
        'content': question.content,
        'create_date': question.create_date,
    }
