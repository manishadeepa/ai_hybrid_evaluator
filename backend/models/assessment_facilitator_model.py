from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func

from backend.database.base import Base


class AssessmentFacilitator(Base):
    __tablename__ = "assessment_facilitators"

    assessment_id = Column(
        Integer,
        ForeignKey("assessments.id", ondelete="CASCADE"),
        primary_key=True,
    )

    facilitator_id = Column(
        Integer,
        ForeignKey("facilitators.id", ondelete="CASCADE"),
        primary_key=True,
    )

    approval_status = Column(
        String(30),
        nullable=False,
        default="pending",
    )

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
    )
