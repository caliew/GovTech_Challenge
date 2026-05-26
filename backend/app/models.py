import datetime
import uuid
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.app.database import Base

class MOMEmployment(Base):
    __tablename__ = "mom_employment"

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, index=True)
    sector = Column(String, index=True)
    employment_change = Column(Integer)  # headcount growth
    unemployment_rate = Column(Float)     # percentage
    median_salary = Column(Float)         # SGD

class SingStatPopulation(Base):
    __tablename__ = "singstat_population"

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, index=True)
    resident_population = Column(Integer)
    median_age = Column(Float)
    dependency_ratio = Column(Float)  # elderly ratio

class SingStatCPI(Base):
    __tablename__ = "singstat_cpi"

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, index=True)
    month = Column(String)  # e.g., "Jan", "Feb"
    cpi_index = Column(Float)
    category = Column(String, index=True)  # e.g., "All Items", "Housing", "Food", "Transport"

class AnalysisRequest(Base):
    __tablename__ = "analysis_requests"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_query = Column(Text, nullable=False)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    logs = relationship("AgentLog", back_populates="request", cascade="all, delete-orphan")
    result = relationship("AnalysisResult", back_populates="request", uselist=False, cascade="all, delete-orphan")

class AgentLog(Base):
    __tablename__ = "agent_logs"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String, ForeignKey("analysis_requests.id"), index=True)
    agent_name = Column(String, index=True)  # Coordinator, Extractor, Analyst
    step_type = Column(String)  # thought, action, observation, status
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    request = relationship("AnalysisRequest", back_populates="logs")

class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id = Column(String, ForeignKey("analysis_requests.id"), unique=True, index=True)
    final_report = Column(Text)  # Markdown text
    chart_data = Column(Text)    # JSON string containing chart options and coordinates
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    request = relationship("AnalysisRequest", back_populates="result")
