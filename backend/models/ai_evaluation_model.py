from sqlalchemy import Column, Integer, DECIMAL, Text, DateTime, ForeignKey, func

from backend.database.base import Base


class AIEvaluation(Base):
    __tablename__ = "ai_evaluations"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    response_id = Column(
        Integer,
        ForeignKey("candidate_responses.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    awarded_marks = Column(
        DECIMAL(6, 2),
        nullable=False,
    )

    percentage = Column(
        DECIMAL(6, 2),
        nullable=True,
    )

    correctness = Column(Text, nullable=True)
    relevance = Column(Text, nullable=True)
    completeness = Column(Text, nullable=True)
    strengths = Column(Text, nullable=True)
    missing_points = Column(Text, nullable=True)
    incorrect_points = Column(Text, nullable=True)
    justification = Column(Text, nullable=True)

    evaluated_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
    )
