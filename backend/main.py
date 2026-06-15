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

setup_logging()

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="JuryDOC API",
    description="API de gestion de documents juridiques — Projet M2 EPISEN.",
    version="1.0.0"
)

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
    trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())
    trace_id_var.set(trace_id)
    
    tenant_id_var.set("system")
    
    response: Response = await call_next(request)
    
    response.headers["X-Trace-ID"] = trace_id
    return response

@app.on_event("startup")
def seed_data():
    db = next(get_db())
    try:
        if db.query(Tenant).count() == 0:
            logging.info("Ajout des cabinets...")
            tenant_a = Tenant(id="cabinet-a", name="Cabinet A - Paris")
            tenant_b = Tenant(id="cabinet-b", name="Cabinet B - Lyon")
            db.add_all([tenant_a, tenant_b])
            db.commit()

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

        if db.query(Document).count() == 0:
            logging.info("Ajout des documents de démo...")
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
            
            import os
            for doc in docs:
                folder = os.path.join(settings.LOCAL_STORAGE_DIR, doc.tenant_id)
                os.makedirs(folder, exist_ok=True)
                with open(os.path.join(folder, doc.filename), "w") as f:
                    f.write(f"This is the confidential text payload of {doc.title}.")
            logging.info("Fichiers de démo créés dans le stockage local.")
            
    except Exception as e:
        logging.error(f"Error seeding database: {e}")
    finally:
        db.close()

@app.post("/api/auth/token")
def login_for_access_token(email: str, db: Session = Depends(get_db)):
    """Mock d'authentification."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Utilisateur introuvable. Utilisez un des emails de démo.")
        
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

from backend.router_docs import router as docs_router
from backend.router_admin import router as admin_router
from backend.router_attacks import router as attacks_router

app.include_router(docs_router)
app.include_router(admin_router)
app.include_router(attacks_router)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "JuryDOC API",
        "tenant_context": "dynamic",
        "docs_url": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    logging.info("Démarrage du serveur...")
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
