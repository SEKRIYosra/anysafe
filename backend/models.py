from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database import Base

class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(String, primary_key=True, index=True) # e.g., 'cabinet-a', 'cabinet-b'
    name = Column(String, nullable=False) # e.g., 'Cabinet A - Paris', 'Cabinet B - Lyon'
    created_at = Column(DateTime, default=datetime.utcnow)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String, unique=True, index=True, nullable=False)
    role = Column(String, nullable=False) # 'admin', 'user', 'auditor'
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    hashed_password = Column(String, nullable=True)
    
    tenant = relationship("Tenant")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False) # GCS uri or local folder path
    content_type = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    uploaded_by = Column(String, nullable=False) # User email
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    is_public = Column(Boolean, default=False)
    
    tenant = relationship("Tenant")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_email = Column(String, nullable=False)
    action = Column(String, nullable=False)
    tenant_id = Column(String, nullable=False)
    ip_address = Column(String, nullable=True)
    status = Column(String, nullable=False) # 'SUCCESS', 'DENIED', 'WARNING'
    trace_id = Column(String, nullable=False)
    details = Column(String, nullable=True)
