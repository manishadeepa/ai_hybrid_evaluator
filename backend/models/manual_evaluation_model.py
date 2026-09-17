from sqlalchemy import Column, Integer, Text, DECIMAL, DateTime, ForeignKey, func

from backend.database.base import Base


class ManualEvaluation(Base):
    __tablename__ = "manual_evaluations"

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

    feedback = Column(
        Text,
        nullable=True,
    )

    evaluated_by = Column(
        Integer,
        ForeignKey("facilitators.id", ondelete="SET NULL"),
        nullable=True,
    )

    evaluated_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
    )
