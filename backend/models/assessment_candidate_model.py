from sqlalchemy import Column, Integer, DateTime, ForeignKey, func

from backend.database.base import Base


class AssessmentCandidate(Base):
    __tablename__ = "assessment_candidates"

    assessment_id = Column(
        Integer,
        ForeignKey("assessments.id", ondelete="CASCADE"),
        primary_key=True,
    )

    candidate_id = Column(
        Integer,
        ForeignKey("candidates.id", ondelete="CASCADE"),
        primary_key=True,
    )

    assigned_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
    )
