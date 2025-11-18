# models.py
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from database import Base


class Question(Base):
    __tablename__ = 'question'

    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    create_date = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
