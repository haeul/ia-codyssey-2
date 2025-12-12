# domain/question/question_router.py
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Question
from schemas import QuestionCreate, QuestionRead

router = APIRouter(
    prefix = '/api/question',
    tags = ['question'],
)


@router.get(
    '/',
    response_model = List[QuestionRead],
)
def question_list(
    db: Session = Depends(get_db),
) -> List[Question]:
    """질문 목록 조회 (ORM 사용)"""
    questions = db.query(Question).all()
    return questions


@router.post(
    '/',
    response_model = QuestionRead,
    status_code = status.HTTP_201_CREATED,
)
def question_create(
    question: QuestionCreate,
    db: Session = Depends(get_db),
) -> Question:
    """질문 등록 (POST, ORM 사용)"""
    new_question = Question(
        title = question.title,
        content = question.content,
    )

    db.add(new_question)
    db.commit()
    db.refresh(new_question)

    return new_question
