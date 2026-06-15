from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    """
    Response schema for a Document.
    `from_attributes=True` permet à Pydantic de lire directement
    les attributs du modèle SQLAlchemy (id, title, size_bytes, ...).
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    filename: str
    content_type: str
    size_bytes: int
    uploaded_by: str
    uploaded_at: datetime
    tenant_id: str
    is_public: bool


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    user_email: str
    action: str
    tenant_id: str
    ip_address: Optional[str] = None
    status: str
    trace_id: str
    details: Optional[str] = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: str
    tenant_id: str