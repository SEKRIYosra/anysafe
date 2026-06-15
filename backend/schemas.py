# Schemas Pydantic pour la serialisation des reponses API.
# Ces classes definissent la structure des donnees renvoyees par les endpoints.
# Le parametre from_attributes=True permet a Pydantic de lire directement
# les attributs des objets SQLAlchemy sans conversion manuelle.

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    """Schema de sortie pour un document juridique.
    Utilise par les endpoints de liste et de telechargement."""
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
    """Schema de sortie pour une entree de journal d'audit.
    Utilise par l'endpoint de consultation des logs admin."""
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
    """Schema de sortie pour un utilisateur.
    Utilise par les endpoints d'administration des utilisateurs."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: str
    tenant_id: str