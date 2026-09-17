from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func

from backend.database.base import Base


class TestCandidate(Base):
    __tablename__ = "test_candidates"

    test_id = Column(
        Integer,
        ForeignKey("tests.id", ondelete="CASCADE"),
        primary_key=True,
    )

    candidate_id = Column(
        Integer,
        ForeignKey("candidates.id", ondelete="CASCADE"),
        primary_key=True,
    )

    status = Column(
        String(30),
        nullable=False,
        default="Assigned",
    )

    started_at = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, nullable=True)

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
    )
