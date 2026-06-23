from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import ForeignKey

DATABASE_URL = "postgresql://migrant_user:password123@localhost/migrant_app"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    country = Column(String)
    direction = Column(String)
    period = Column(Integer)
    visa_expiry = Column(String)
    registration_expiry = Column(String)
    hashed_password = Column(String)
    email = Column(String)

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    deadline = Column(String)
    status = Column(String)
    student_id = Column(Integer, ForeignKey("students.id"))

Base.metadata.create_all(engine)