from sqlalchemy import Column, Integer, String, Text, DECIMAL, DateTime, ForeignKey, func

from backend.database.base import Base


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    test_id = Column(
        Integer,
        ForeignKey("tests.id", ondelete="CASCADE"),
        nullable=False,
    )

    question_number = Column(Integer, nullable=False)
    question_text = Column(Text, nullable=False)
    marks = Column(DECIMAL(6, 2), nullable=False)

    co = Column(String(50), nullable=True)
    lo = Column(String(50), nullable=True)
    knowledge_type = Column(String(100), nullable=True)
    domain = Column(String(100), nullable=True)
    rbt_level = Column(String(50), nullable=True)

    answer_key = Column(Text, nullable=True)

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
    )

    updated_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
