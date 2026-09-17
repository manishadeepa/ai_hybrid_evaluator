from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, func

from backend.database.base import Base


class CandidateResponse(Base):
    __tablename__ = "candidate_responses"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    test_id = Column(
        Integer,
        ForeignKey("tests.id", ondelete="CASCADE"),
        nullable=False,
    )

    candidate_id = Column(
        Integer,
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
    )

    question_id = Column(
        Integer,
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
    )

    answer_text = Column(
        Text,
        nullable=True,
    )

    submitted_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
    )
