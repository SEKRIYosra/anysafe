import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

from backend.database import Base, get_db
from backend.main import app
from backend.models import Tenant, User, Document, AuditLog
from backend.auth import create_access_token
from backend.config import settings

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        t_a = Tenant(id="cabinet-a", name="Cabinet A - Paris")
        t_b = Tenant(id="cabinet-b", name="Cabinet B - Lyon")
        db.add_all([t_a, t_b])
        
        u_admin_a = User(email="nour.admin@cabinet-a.fr", role="admin", tenant_id="cabinet-a")
        u_user_a = User(email="aya.user@cabinet-a.fr", role="user", tenant_id="cabinet-a")
        u_auditor_a = User(email="yosra.auditor@cabinet-a.fr", role="auditor", tenant_id="cabinet-a")
        u_user_b = User(email="avocat.user@cabinet-b.fr", role="user", tenant_id="cabinet-b")
        db.add_all([u_admin_a, u_user_a, u_auditor_a, u_user_b])
        
        doc_a = Document(
            id=101, title="Doc Cabinet A", filename="doc_a.pdf",
            file_path="./local_storage/cabinet-a/doc_a.pdf", content_type="application/pdf",
            size_bytes=100, uploaded_by="nour.admin@cabinet-a.fr", tenant_id="cabinet-a"
        )
        doc_b = Document(
            id=4, title="Doc Cabinet B", filename="doc_b.pdf",
            file_path="./local_storage/cabinet-b/doc_b.pdf", content_type="application/pdf",
            size_bytes=200, uploaded_by="avocat.user@cabinet-b.fr", tenant_id="cabinet-b"
        )
        db.add_all([doc_a, doc_b])
        db.commit()
        
        os.makedirs("./local_storage/cabinet-a", exist_ok=True)
        os.makedirs("./local_storage/cabinet-b", exist_ok=True)
        with open("./local_storage/cabinet-a/doc_a.pdf", "w") as f:
            f.write("cabinet a contents")
        with open("./local_storage/cabinet-b/doc_b.pdf", "w") as f:
            f.write("cabinet b contents")
            
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
        if os.path.exists("./test.db"):
            os.remove("./test.db")
        if os.path.exists("./local_storage/cabinet-a/doc_a.pdf"):
            os.remove("./local_storage/cabinet-a/doc_a.pdf")
        if os.path.exists("./local_storage/cabinet-b/doc_b.pdf"):
            os.remove("./local_storage/cabinet-b/doc_b.pdf")

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

def get_auth_headers(email: str, role: str, tenant_id: str):
    token = create_access_token({"email": email, "role": role, "tenant_id": tenant_id})
    return {"Authorization": f"Bearer {token}"}

def test_list_documents_tenant_isolation():
    """Test cloisonnement des documents par cabinet."""
    headers = get_auth_headers("aya.user@cabinet-a.fr", "user", "cabinet-a")
    response = client.get("/api/documents", headers=headers)
    assert response.status_code == 200
    docs = response.json()
    assert len(docs) == 1
    assert docs[0]["id"] == 101
    assert docs[0]["tenant_id"] == "cabinet-a"

def test_download_document_cross_tenant_blocked():
    """Test blocage IDOR inter-cabinet."""
    headers = get_auth_headers("aya.user@cabinet-a.fr", "user", "cabinet-a")
    response = client.get("/api/documents/4", headers=headers)
    assert response.status_code == 403
    assert "Cross-Tenant Block" in response.json()["detail"]

def test_rbac_restrictions():
    """Test des restrictions RBAC."""
    headers_auditor = get_auth_headers("yosra.auditor@cabinet-a.fr", "auditor", "cabinet-a")
    files = {"file": ("test.pdf", b"test content", "application/pdf")}
    response = client.post("/api/documents", data={"title": "Test Upload"}, files=files, headers=headers_auditor)
    assert response.status_code == 403
    
    response = client.delete("/api/documents/101", headers=headers_auditor)
    assert response.status_code == 403
    
    headers_user = get_auth_headers("aya.user@cabinet-a.fr", "user", "cabinet-a")
    response = client.delete("/api/documents/101", headers=headers_user)
    assert response.status_code == 403
    
    headers_admin = get_auth_headers("nour.admin@cabinet-a.fr", "admin", "cabinet-a")
    response = client.delete("/api/documents/101", headers=headers_admin)
    assert response.status_code == 200

def test_trace_id_injection():
    """Test présence X-Trace-ID."""
    response = client.get("/")
    assert response.status_code == 200
    assert "X-Trace-ID" in response.headers
    assert len(response.headers["X-Trace-ID"]) > 0

def test_summarize_document_tenant_isolation():
    """Test isolation cloisonnement pour la synthèse IA."""
    headers = get_auth_headers("aya.user@cabinet-a.fr", "user", "cabinet-a")
    response = client.post("/api/documents/4/summarize", headers=headers)
    assert response.status_code == 403

def test_summarize_document_success(monkeypatch):
    """Test succès génération synthèse IA."""
    class MockResponse:
        @property
        def text(self):
            return "Ceci est un résumé juridique simulé en français."

    def mock_generate_content(*args, **kwargs):
        return MockResponse()

    from backend import router_docs
    monkeypatch.setattr(router_docs.client.models, "generate_content", mock_generate_content)
    
    headers = get_auth_headers("aya.user@cabinet-a.fr", "user", "cabinet-a")
    response = client.post("/api/documents/101/summarize", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["doc_id"] == 101
    assert "simulé" in data["summary"]
