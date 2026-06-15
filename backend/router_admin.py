import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import AuditLog, User
from backend.schemas import AuditLogOut, UserOut
from backend.auth import get_current_user, RequireRole

router = APIRouter(prefix="/api/admin", tags=["Admin & Audit"])

@router.get("/logs", response_model=List[AuditLogOut])
def get_audit_logs(
    request: Request,
    current_user = Depends(RequireRole(["admin", "auditor"])),
    db: Session = Depends(get_db)
):
    """Récupération des logs d'audit du tenant."""
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
    """Liste les utilisateurs du tenant."""
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
    """Création d'un nouvel utilisateur dans le tenant."""
    if role not in ["admin", "user", "auditor"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'admin', 'user', or 'auditor'")
        
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
        
    new_user = User(
        email=email,
        role=role,
        tenant_id=current_user.tenant_id
    )
    db.add(new_user)
    
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