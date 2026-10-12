from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Enum
from app.db import Base

import enum


class UserRole(str, enum.Enum):
    student = "student"
    staff = "staff"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.student)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
