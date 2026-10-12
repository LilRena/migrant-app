from sqlalchemy import Column, Integer, String, Date, ForeignKey
from app.db import Base


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    country_code = Column(String(10))
    faculty = Column(String)
    course = Column(Integer)
    arrival_date = Column(Date)
    visa_expiry = Column(Date)
    registration_expiry = Column(Date)
