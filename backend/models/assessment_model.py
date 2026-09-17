from sqlalchemy import Column, Integer, String, Date, DateTime, func

from backend.database.base import Base


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(150), nullable=False)
    assessment_date = Column(Date, nullable=True)
    status = Column(String(30), nullable=False, default="Draft")
    approval_status = Column(String(30), nullable=False, default="pending")
    completed_at = Column(DateTime, nullable=True)

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
    )

    updated_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
