# Point d'entree principal de l'API JuryDOC.
# Ce fichier configure l'application FastAPI, les middlewares,
# initialise la base de donnees avec des donnees de demonstration,
# et enregistre les differents routeurs (documents, admin, attaques).

import logging
import uuid
from fastapi import FastAPI, Request, Response, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.config import settings
from backend.logging_config import setup_logging, trace_id_var, tenant_id_var
from backend.database import engine, Base, get_db
from backend.models import Tenant, User, Document
from backend.auth import create_access_token

# Initialisation du systeme de logs JSON structure
setup_logging()

# Creation des tables en base de donnees si elles n'existent pas encore
Base.metadata.create_all(bind=engine)

# Creation de l'application FastAPI avec les metadonnees de documentation
app = FastAPI(
    title="JuryDOC API",
    description="API de gestion de documents juridiques -- Projet M2 EPISEN.",
    version="1.0.0"
)

# Configuration du middleware CORS.
# En production, il faudrait restreindre allow_origins aux domaines autorises.
# Ici, on autorise tout pour faciliter le developpement.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Trace-ID"]
)


@app.middleware("http")
async def trace_id_middleware(request: Request, call_next):
    """Middleware qui attribue un identifiant de trace unique a chaque requete.
    Si le client envoie un header X-Trace-ID, on le reutilise.
    Sinon, on en genere un nouveau (UUID).
    Ce trace_id est ensuite disponible dans tous les logs et les audit logs."""

    trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())
    trace_id_var.set(trace_id)
    
    # Par defaut, le tenant est "system" (avant l'authentification)
    tenant_id_var.set("system")
    
    response: Response = await call_next(request)
    
    # On renvoie le trace_id dans la reponse pour que le client puisse le suivre
    response.headers["X-Trace-ID"] = trace_id
    return response


@app.on_event("startup")
def seed_data():
    """Insertion de donnees de demonstration au demarrage de l'application.
    Cree deux cabinets, six utilisateurs et trois documents d'exemple.
    Cette fonction ne s'execute que si la base est vide."""

    db = next(get_db())
    try:
        # Creation des cabinets de demonstration
        if db.query(Tenant).count() == 0:
            logging.info("Ajout des cabinets...")
            tenant_a = Tenant(id="cabinet-a", name="Cabinet A - Paris")
            tenant_b = Tenant(id="cabinet-b", name="Cabinet B - Lyon")
            db.add_all([tenant_a, tenant_b])
            db.commit()

        # Creation des utilisateurs de demonstration avec differents roles
        if db.query(User).count() == 0:
            logging.info("Ajout des utilisateurs...")
            users = [
                User(email="nour.admin@cabinet-a.fr", role="admin", tenant_id="cabinet-a"),
                User(email="aya.user@cabinet-a.fr", role="user", tenant_id="cabinet-a"),
                User(email="yosra.auditor@cabinet-a.fr", role="auditor", tenant_id="cabinet-a"),
                User(email="avocat.admin@cabinet-b.fr", role="admin", tenant_id="cabinet-b"),
                User(email="avocat.user@cabinet-b.fr", role="user", tenant_id="cabinet-b"),
                User(email="avocat.auditor@cabinet-b.fr", role="auditor", tenant_id="cabinet-b"),
            ]
            db.add_all(users)
            db.commit()

        # Creation des documents juridiques de demonstration
        if db.query(Document).count() == 0:
            logging.info("Ajout des documents de demo...")
            docs = [
                Document(
                    title="Case File - Dupont vs. State",
                    filename="dupont_vs_state.pdf",
                    file_path="./local_storage/cabinet-a/dupont_vs_state.pdf",
                    content_type="application/pdf",
                    size_bytes=1024,
                    uploaded_by="nour.admin@cabinet-a.fr",
                    tenant_id="cabinet-a"
                ),
                Document(
                    title="Acquisition Contract - ANYSafe Tech",
                    filename="anysafe_contract.pdf",
                    file_path="./local_storage/cabinet-a/anysafe_contract.pdf",
                    content_type="application/pdf",
                    size_bytes=2048,
                    uploaded_by="aya.user@cabinet-a.fr",
                    tenant_id="cabinet-a"
                ),
                Document(
                    title="Divorce Case - Martin vs. Martin",
                    filename="martin_divorce.pdf",
                    file_path="./local_storage/cabinet-b/martin_divorce.pdf",
                    content_type="application/pdf",
                    size_bytes=512,
                    uploaded_by="avocat.user@cabinet-b.fr",
                    tenant_id="cabinet-b"
                ),
            ]
            db.add_all(docs)
            db.commit()
            
            # Creation des fichiers physiques correspondants dans le stockage local
            import os
            for doc in docs:
                folder = os.path.join(settings.LOCAL_STORAGE_DIR, doc.tenant_id)
                os.makedirs(folder, exist_ok=True)
                with open(os.path.join(folder, doc.filename), "w") as f:
                    f.write(f"This is the confidential text payload of {doc.title}.")
            logging.info("Fichiers de demo crees dans le stockage local.")
            
    except Exception as e:
        logging.error(f"Error seeding database: {e}")
    finally:
        db.close()


@app.post("/api/auth/token")
def login_for_access_token(email: str, db: Session = Depends(get_db)):
    """Endpoint d'authentification simplifie (version demo).
    Recoit un email et retourne un token JWT si l'utilisateur existe.
    En production, il faudrait verifier un mot de passe ou utiliser un fournisseur OAuth."""

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Utilisateur introuvable. Utilisez un des emails de demo.")
        
    # On encode l'email, le role et le tenant dans le token
    token_claims = {
        "email": user.email,
        "role": user.role,
        "tenant_id": user.tenant_id
    }
    access_token = create_access_token(data=token_claims)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "email": user.email,
            "role": user.role,
            "tenant_id": user.tenant_id
        }
    }

# Enregistrement des routeurs pour chaque domaine fonctionnel
from backend.router_docs import router as docs_router
from backend.router_admin import router as admin_router
from backend.router_attacks import router as attacks_router

app.include_router(docs_router)
app.include_router(admin_router)
app.include_router(attacks_router)


@app.get("/")
def read_root():
    """Endpoint racine de l'API. Permet de verifier que le service est en ligne."""
    return {
        "status": "online",
        "service": "JuryDOC API",
        "tenant_context": "dynamic",
        "docs_url": "/docs"
    }

# Lancement du serveur en mode developpement
if __name__ == "__main__":
    import uvicorn
    logging.info("Demarrage du serveur...")
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
