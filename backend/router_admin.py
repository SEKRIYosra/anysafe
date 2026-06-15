# Routeur d'administration et d'audit.
# Contient les endpoints reserves aux administrateurs et auditeurs :
# consultation des logs d'audit, liste et creation d'utilisateurs.

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import AuditLog, User
from backend.schemas import AuditLogOut, UserOut
from backend.auth import get_current_user, RequireRole

# Prefixe /api/admin pour tous les endpoints de ce routeur
router = APIRouter(prefix="/api/admin", tags=["Admin & Audit"])


@router.get("/logs", response_model=List[AuditLogOut])
def get_audit_logs(
    request: Request,
    current_user = Depends(RequireRole(["admin", "auditor"])),
    db: Session = Depends(get_db)
):
    """Recupere tous les logs d'audit du cabinet de l'utilisateur connecte.
    Accessible uniquement aux administrateurs et auditeurs.
    Les logs sont tries du plus recent au plus ancien."""

    logs = db.query(AuditLog)\
        .filter(AuditLog.tenant_id == current_user.tenant_id)\
        .order_by(AuditLog.timestamp.desc())\
        .all()
        
    return logs


@router.get("/users", response_model=List[UserOut])
def get_tenant_users(
    current_user = Depends(RequireRole(["admin"])),
    db: Session = Depends(get_db)
):
    """Liste tous les utilisateurs du cabinet de l'admin connecte.
    Reserve aux administrateurs uniquement."""

    users = db.query(User).filter(User.tenant_id == current_user.tenant_id).all()
    return users


@router.post("/users", response_model=UserOut)
def create_tenant_user(
    request: Request,
    email: str,
    role: str,
    current_user = Depends(RequireRole(["admin"])),
    db: Session = Depends(get_db)
):
    """Cree un nouvel utilisateur dans le cabinet de l'admin connecte.
    Verifie que le role est valide et que l'email n'existe pas deja.
    L'action est enregistree dans les logs d'audit."""

    # Verification que le role demande est un role valide
    if role not in ["admin", "user", "auditor"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'admin', 'user', or 'auditor'")
        
    # Verification que l'email n'est pas deja utilise
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
        
    # Creation de l'utilisateur dans le meme cabinet que l'admin
    new_user = User(
        email=email,
        role=role,
        tenant_id=current_user.tenant_id
    )
    db.add(new_user)
    
    # Enregistrement de l'action dans les logs d'audit
    log_entry = AuditLog(
        user_email=current_user.email,
        action="CREATE_USER",
        tenant_id=current_user.tenant_id,
        ip_address=request.client.host if request.client else "unknown",
        status="SUCCESS",
        trace_id=request.headers.get("x-trace-id", "system"),
        details=f"Created user {email} with role {role}"
    )
    db.add(log_entry)
    
    db.commit()
    db.refresh(new_user)
    return new_user