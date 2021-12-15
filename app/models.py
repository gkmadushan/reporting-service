# coding: utf-8
from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base    

Base = declarative_base()
metadata = Base.metadata


class LessonLearntReport(Base):
    __tablename__ = 'lesson_learnt_report'

    id = Column(UUID, primary_key=True)
    description = Column(String(6000), nullable=False)
    submitted_at = Column(DateTime, nullable=False)
    issue_id = Column(UUID, nullable=False)
    title = Column(String(2000), nullable=False)


class Reference(Base):
    __tablename__ = 'reference'

    id = Column(UUID, primary_key=True)
    reference = Column(String(250), nullable=False, index=True)
    type = Column(String(100), nullable=False)
    report = Column(ForeignKey('lesson_learnt_report.id'), nullable=False)

    lesson_learnt_report = relationship('LessonLearntReport')