# Modeles de la base de donnees (tables SQL).
# Ces classes representent la structure des donnees de l'application.
# L'architecture est multi-tenant : chaque cabinet (Tenant) a ses propres
# utilisateurs, documents et logs d'audit.

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database import Base


class Tenant(Base):
    """Represente un cabinet d'avocats (locataire).
    C'est l'unite d'isolation principale : chaque tenant a ses propres
    donnees, et aucun tenant ne peut acceder aux donnees d'un autre."""
    __tablename__ = "tenants"
    
    # Identifiant unique du cabinet, par exemple "cabinet-a" ou "cabinet-b"
    id = Column(String, primary_key=True, index=True)
    # Nom lisible du cabinet, par exemple "Cabinet A - Paris"
    name = Column(String, nullable=False)
    # Date de creation de l'enregistrement
    created_at = Column(DateTime, default=datetime.utcnow)


class User(Base):
    """Represente un utilisateur de la plateforme.
    Chaque utilisateur est rattache a un seul cabinet (tenant)
    et possede un role qui determine ses droits d'acces."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    # Adresse email unique, utilisee comme identifiant de connexion
    email = Column(String, unique=True, index=True, nullable=False)
    # Role de l'utilisateur : "admin", "user" ou "auditor"
    role = Column(String, nullable=False)
    # Cle etrangere vers le cabinet auquel l'utilisateur appartient
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    # Mot de passe hashe (non utilise dans la version demo, authentification par email)
    hashed_password = Column(String, nullable=True)
    
    # Relation vers le modele Tenant pour acceder aux infos du cabinet
    tenant = relationship("Tenant")


class Document(Base):
    """Represente un document juridique stocke dans la plateforme.
    Chaque document est isole par tenant : seuls les utilisateurs
    du meme cabinet peuvent le consulter, le telecharger ou le supprimer."""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    # Titre descriptif du document
    title = Column(String, nullable=False)
    # Nom du fichier original
    filename = Column(String, nullable=False)
    # Chemin de stockage : chemin local en dev, URI GCS en production
    file_path = Column(String, nullable=False)
    # Type MIME du fichier (ex: application/pdf)
    content_type = Column(String, nullable=False)
    # Taille du fichier en octets
    size_bytes = Column(Integer, nullable=False)
    # Email de l'utilisateur qui a televerse le document
    uploaded_by = Column(String, nullable=False)
    # Date de telechargement
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    # Cabinet proprietaire du document
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    # Indique si le document est accessible publiquement (par defaut non)
    is_public = Column(Boolean, default=False)
    
    tenant = relationship("Tenant")


class AuditLog(Base):
    """Represente une entree dans le journal d'audit.
    Chaque action importante (consultation, telechargement, suppression,
    tentative d'acces non autorise) est enregistree ici pour la tracabilite."""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    # Date et heure de l'action
    timestamp = Column(DateTime, default=datetime.utcnow)
    # Email de l'utilisateur qui a effectue l'action
    user_email = Column(String, nullable=False)
    # Type d'action effectuee (ex: LIST_DOCUMENTS, DOWNLOAD_DOCUMENT, ACCESS_VIOLATION)
    action = Column(String, nullable=False)
    # Cabinet concerne par l'action
    tenant_id = Column(String, nullable=False)
    # Adresse IP du client
    ip_address = Column(String, nullable=True)
    # Resultat de l'action : "SUCCESS", "DENIED" ou "WARNING"
    status = Column(String, nullable=False)
    # Identifiant de trace unique pour suivre la requete de bout en bout
    trace_id = Column(String, nullable=False)
    # Details complementaires sur l'action
    details = Column(String, nullable=True)
