# Module d'authentification et d'autorisation.
# Gere la creation et la verification des tokens JWT,
# l'identification de l'utilisateur courant, le controle d'acces
# par role (RBAC) et l'isolation entre cabinets (multi-tenant).

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
from backend.config import settings
from backend.database import get_db
from backend.models import User
from backend.logging_config import tenant_id_var

# Configuration du schema OAuth2.
# auto_error=False permet de gerer manuellement le cas ou le token est absent.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token", auto_error=False)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Cree un token JWT signe contenant les informations de l'utilisateur.
    Le token inclut l'email, le role et le tenant_id, ainsi qu'une date d'expiration."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Par defaut, le token expire apres le delai configure dans les settings
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """Decode et verifie un token JWT.
    Leve une erreur 401 si le token est invalide ou expire."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Recupere l'utilisateur courant a partir du token JWT.
    Cette fonction est utilisee comme dependance FastAPI dans les endpoints proteges.
    Si l'utilisateur n'existe pas encore en base, il est cree automatiquement
    (utile pour les premiers acces apres authentification)."""

    # Verification que le token est bien present dans la requete
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Decodage du token pour extraire les informations utilisateur
    payload = decode_access_token(token)
    email: str = payload.get("email")
    tenant_id: str = payload.get("tenant_id")
    
    # Le token doit obligatoirement contenir un email et un tenant_id
    if email is None or tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # On met a jour la variable de contexte du tenant pour les logs
    tenant_id_var.set(tenant_id)
    
    # Recherche de l'utilisateur en base de donnees
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        # Si l'utilisateur n'existe pas, on le cree avec les infos du token
        role = payload.get("role", "user")
        user = User(email=email, role=role, tenant_id=tenant_id)
        db.add(user)
        db.commit()
        db.refresh(user)
        
    return user


class RequireRole:
    """Classe de verification des roles (RBAC).
    Utilisee comme dependance FastAPI pour restreindre l'acces
    a certains endpoints selon le role de l'utilisateur.
    Exemple : RequireRole(["admin"]) n'autorise que les administrateurs."""

    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles
        
    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        # Si le role de l'utilisateur n'est pas dans la liste autorisee, acces refuse
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Access restricted. Required roles: {self.allowed_roles}. Your role: {current_user.role}"
            )
        return current_user


def enforce_tenant_isolation(requested_tenant_id: str, current_user: User = Depends(get_current_user)):
    """Verifie que l'utilisateur accede uniquement aux ressources de son propre cabinet.
    Bloque toute tentative d'acces cross-tenant (isolation multi-tenant)."""
    if current_user.tenant_id != requested_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Security Violation: Access to other tenant's resources is strictly prohibited (Cross-Tenant Block)."
        )
    return requested_tenant_id
