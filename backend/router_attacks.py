import logging
import time
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Document, AuditLog, User
from backend.auth import get_current_user, RequireRole, decode_access_token, oauth2_scheme
from backend.logging_config import trace_id_var

router = APIRouter(prefix="/api/attacks", tags=["Attack Simulator"])

token_blacklist = set()

rate_limit_hits = {}

@router.get("/idor/vulnerable/{doc_id}")
def idor_vulnerable(doc_id: int, db: Session = Depends(get_db)):
    """Endpoint vulnérable IDOR."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        "status": "EXPLOITED",
        "description": "Accès sans vérification du tenant_id — les métadonnées du document sont exposées.",
        "document": {
            "id": doc.id,
            "title": doc.title,
            "filename": doc.filename,
            "tenant_id": doc.tenant_id,
            "uploaded_by": doc.uploaded_by
        }
    }

@router.get("/idor/secured/{doc_id}")
def idor_secured(
    doc_id: int, 
    request: Request,
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Endpoint sécurisé contre IDOR."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if doc.tenant_id != current_user.tenant_id:
        # On enregistre la tentative dans l'audit log
        trace_id = trace_id_var.get()
        log_entry = AuditLog(
            user_email=current_user.email,
            action="ATTACK_IDOR_BLOCKED",
            tenant_id=current_user.tenant_id,
            ip_address=request.client.host if request.client else "unknown",
            status="DENIED",
            trace_id=trace_id,
            details=f"IDOR Attack blocked: User tried to access Document {doc_id} belonging to {doc.tenant_id}"
        )
        db.add(log_entry)
        db.commit()
        
        logging.warning(f"[SECURITY ALERT] Cross-tenant access attempt by {current_user.email}! TraceID: {trace_id}")
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Security Violation: Access to other tenant's documents is strictly prohibited (Cross-Tenant Block)."
        )
        
    return {
        "status": "SECURED",
        "description": "Accès autorisé : le document appartient bien à votre cabinet.",
        "document": {
            "id": doc.id,
            "title": doc.title,
            "tenant_id": doc.tenant_id
        }
    }

@router.post("/privilege-escalation/vulnerable/{doc_id}")
def privilege_escalation_vulnerable(doc_id: int, role: str, db: Session = Depends(get_db)):
    """Endpoint vulnérable contournement RBAC."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    # Suppression sans vérification de rôle (RBAC bypassé)
    db.delete(doc)
    db.commit()
    return {
        "status": "EXPLOITED",
        "description": f"Document {doc_id} supprimé sans vérification de rôle (role={role} accepté)."
    }

@router.post("/token-replay/simulate-logout")
def simulate_logout(token: str = Depends(oauth2_scheme)):
    """Simulation de déconnexion."""
    if token:
        token_blacklist.add(token)
    return {"status": "success", "message": "Token blacklisted (logged out)"}

@router.get("/token-replay/vulnerable")
def token_replay_vulnerable(token: str = Depends(oauth2_scheme)):
    """Endpoint vulnérable au rejeu de session."""
    payload = decode_access_token(token)
    return {
        "status": "EXPLOITED",
        "description": "Jeton révoqué accepté par le serveur — l'attaquant peut se faire passer pour l'utilisateur.",
        "user_email": payload.get("email"),
        "tenant_id": payload.get("tenant_id")
    }

@router.get("/token-replay/secured")
def token_replay_secured(token: str = Depends(oauth2_scheme)):
    """Endpoint sécurisé contre le rejeu de session."""
    if token in token_blacklist:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token Replay Blocked: The provided token has been revoked or blacklisted."
        )
    payload = decode_access_token(token)
    return {
        "status": "SECURED",
        "description": "Jeton valide et non révoqué.",
        "user_email": payload.get("email")
    }

@router.get("/public-leak/vulnerable/{filename}")
def public_leak_vulnerable(filename: str):
    """Vérification fuite stockage publique."""
    return {
        "status": "EXPLOITED",
        "description": "Bucket accessible sans authentification — Public Access Prevention désactivée.",
        "filename": filename,
        "content": "CONTENU CONFIDENTIEL DU DOSSIER JURIDIQUE (BUCKET PUBLIC NON CHIFFRÉ)"
    }

@router.get("/public-leak/secured/{filename}")
def public_leak_secured(token: Optional[str] = Depends(oauth2_scheme)):
    """Vérification accès stockage authentifié."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access Denied: Object storage has Public Access Prevention (PAP) enabled. Enforce authentication."
        )
    payload = decode_access_token(token)
    return {
        "status": "SECURED",
        "description": "Public Access Prevention activée. Accès via token uniquement. Contenu déchiffré via compte de service.",
        "content": "CONTENU CONFIDENTIEL DU DOSSIER (CHIFFRÉ KMS CMEK)"
    }

@router.get("/dos/simulate")
def dos_simulate(request: Request, client_id: str, mode: str, db: Session = Depends(get_db)):
    """Simulation de DoS / Rate limiting."""
    now = time.time()
    
    if mode == "vulnerable":
        return {
            "status": "EXPLOITED",
            "description": "Unlimited hits allowed. High risk of resource exhaustion / DoS.",
            "requests_processed": 9999
        }
        
    # Mode sécurisé : on applique le rate limiter
    hits = rate_limit_hits.get(client_id, [])
    # On garde uniquement les hits des 10 dernières secondes
    hits = [h for h in hits if now - h < 10]
    hits.append(now)
    rate_limit_hits[client_id] = hits
    
    if len(hits) > 5:
        # Alerte déclenchée, on log dans l'audit
        trace_id = trace_id_var.get()
        log_entry = AuditLog(
            user_email=f"client-{client_id}",
            action="RATE_LIMIT_EXCEEDED",
            tenant_id="system",
            ip_address=request.client.host if request.client else "unknown",
            status="DENIED",
            trace_id=trace_id,
            details=f"Rate limiting alert: client {client_id} sent {len(hits)} requests in 10s (limit is 5)"
        )
        db.add(log_entry)
        db.commit()
        
        logging.error(f"[SECURITY ALERT] DoS/Rate-Limit abuse detected from {client_id}! TraceID: {trace_id}")
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Security warning: Too many requests in a short period."
        )
        
    return {
        "status": "SECURED",
        "description": f"Request processed. Rate-limit checks: {len(hits)}/5 requests used.",
        "hits_left": 5 - len(hits)
    }

@router.get("/secret-leak/simulate")
def secret_leak_simulate(mode: str):
    """Simulation de fuite de secrets."""
    if mode == "vulnerable":
        debug_log = "DEBUG: Connecting to PostgreSQL on 10.0.1.5 with user=db_admin password=SuperSecretPassword2026!..."
        return {
            "status": "EXPLOITED",
            "description": "Secrets leaked in application console/source logs!",
            "leaked_data": debug_log
        }
        
    return {
        "status": "SECURED",
        "description": "Secrets correctement masqués — injectés via GCP Secret Manager au runtime.",
        "log_output": "DEBUG: Connexion à PostgreSQL via compte de service OAuth... [MASQUÉ]"
    }
