from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    prn = Column(String(64), unique=True, nullable=False)
    name = Column(String(256), nullable=False)
    password_hash = Column(String(256), nullable=True)
    role = Column(String(32), nullable=False, default="student")
    branch = Column(String(128), nullable=True)
    branch_code = Column(String(16), nullable=True)
    student_class = Column(String(64), nullable=True)
    semester = Column(String(8), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    active = Column(Boolean, default=True)
    sessions = relationship("ExamSession", back_populates="student")

class QuestionPaper(Base):
    __tablename__ = "question_papers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(256), nullable=False)
    branch = Column(String(128), nullable=False)
    branch_code = Column(String(16), nullable=False)
    semester = Column(String(8), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    active = Column(Boolean, default=False)
    questions = relationship("MCQQuestion", back_populates="paper")
    timetable_entries = relationship("TimetableEntry", back_populates="paper")

class MCQQuestion(Base):
    __tablename__ = "mcq_questions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, ForeignKey("question_papers.id", ondelete="CASCADE"), nullable=False)
    text = Column(Text, nullable=False)
    option_a = Column(Text, nullable=False)
    option_b = Column(Text, nullable=False)
    option_c = Column(Text, nullable=False)
    option_d = Column(Text, nullable=False)
    answer_key = Column(String(4), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    paper = relationship("QuestionPaper", back_populates="questions")

class ExamSession(Base):
    __tablename__ = "exam_sessions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    paper_id = Column(Integer, ForeignKey("question_papers.id", ondelete="SET NULL"), nullable=True)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    answers_json = Column(Text, nullable=True)
    score = Column(Integer, nullable=True)
    completed = Column(Boolean, default=False)
    student = relationship("User", back_populates="sessions")

class IPConfig(Base):
    __tablename__ = "ip_configs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    allowed_ips = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)

class TimetableEntry(Base):
    __tablename__ = "timetable_entries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, ForeignKey("question_papers.id", ondelete="CASCADE"), nullable=False)
    start_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=False)
    paper = relationship("QuestionPaper", back_populates="timetable_entries")

class AppConfig(Base):
    __tablename__ = "app_config"
    id = Column(Integer, primary_key=True, autoincrement=True)
    countdown_minutes = Column(Integer, default=30)
    last_updated = Column(DateTime, default=datetime.utcnow)
