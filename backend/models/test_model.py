from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, func

from backend.database.base import Base


class Test(Base):
    __tablename__ = "tests"

    id = Column(Integer, primary_key=True, autoincrement=True)

    assessment_id = Column(
        Integer,
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
    )

    test_name = Column(String(150), nullable=False)
    test_type = Column(String(30), nullable=False, default="Formative")
    test_date = Column(Date, nullable=True)
    status = Column(String(30), nullable=False, default="Draft")

    question_paper_filename = Column(String(255), nullable=True)

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
    )

    updated_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
