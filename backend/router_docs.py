import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session
import io

from backend.database import get_db
from backend.models import Document, AuditLog
from backend.schemas import DocumentOut
from backend.auth import get_current_user, RequireRole, enforce_tenant_isolation
from backend.storage import storage_manager
from backend.logging_config import trace_id_var
from backend.config import settings
from google import genai
client = genai.Client(api_key=settings.GEMINI_API_KEY)


router = APIRouter(prefix="/api/documents", tags=["Documents"])

def write_audit_log(db: Session, request: Request, email: str, action: str, tenant_id: str, status: str, details: str):
    ip = request.client.host if request.client else "unknown"
    trace_id = trace_id_var.get()
    
    log_entry = AuditLog(
        user_email=email,
        action=action,
        tenant_id=tenant_id,
        ip_address=ip,
        status=status,
        trace_id=trace_id,
        details=details
    )
    db.add(log_entry)
    db.commit()
    logging.info(f"Audit log saved: {action} - Status: {status} - Tenant: {tenant_id} - TraceID: {trace_id}")

@router.get("", response_model=List[DocumentOut])
def list_documents(
    request: Request,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Liste les documents du cabinet (tenant)."""
    docs = db.query(Document).filter(Document.tenant_id == current_user.tenant_id).all()
    
    write_audit_log(
        db, request, current_user.email, "LIST_DOCUMENTS", 
        current_user.tenant_id, "SUCCESS", f"Listed {len(docs)} documents"
    )
    return docs

@router.post("", response_model=DocumentOut)
def upload_document(
    request: Request,
    title: str = Form(...),
    file: UploadFile = File(...),
    current_user = Depends(RequireRole(["admin", "user"])),
    db: Session = Depends(get_db)
):
    """Importe un document dans le cabinet (RBAC restreint pour auditor)."""
    try:
        content = file.file.read()
        size_bytes = len(content)
        
        file_path = storage_manager.save_file(current_user.tenant_id, file.filename, content)
        
        db_doc = Document(
            title=title,
            filename=file.filename,
            file_path=file_path,
            content_type=file.content_type or "application/octet-stream",
            size_bytes=size_bytes,
            uploaded_by=current_user.email,
            tenant_id=current_user.tenant_id
        )
        db.add(db_doc)
        db.commit()
        db.refresh(db_doc)
        
        write_audit_log(
            db, request, current_user.email, "UPLOAD_DOCUMENT", 
            current_user.tenant_id, "SUCCESS", f"Uploaded document: {title} (ID: {db_doc.id})"
        )
        return db_doc
        
    except Exception as e:
        write_audit_log(
            db, request, current_user.email, "UPLOAD_DOCUMENT", 
            current_user.tenant_id, "FAILED", f"Failed to upload: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )

@router.get("/{doc_id}")
def download_document(
    doc_id: int,
    request: Request,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Téléchargement d'un document (avec vérification du tenant)."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        write_audit_log(
            db, request, current_user.email, "DOWNLOAD_DOCUMENT", 
            current_user.tenant_id, "FAILED", f"Document {doc_id} not found"
        )
        raise HTTPException(status_code=404, detail="Document not found")
    
    if doc.tenant_id != current_user.tenant_id:
        write_audit_log(
            db, request, current_user.email, "ACCESS_VIOLATION", 
            current_user.tenant_id, "DENIED", 
            f"Unauthorized attempt to access Document {doc_id} from Tenant {doc.tenant_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Security Violation: Access to other tenant's documents is strictly prohibited (Cross-Tenant Block)."
        )
        
    try:
        file_bytes = storage_manager.read_file(doc.tenant_id, doc.filename)
        write_audit_log(
            db, request, current_user.email, "DOWNLOAD_DOCUMENT", 
            current_user.tenant_id, "SUCCESS", f"Downloaded document: {doc.title} (ID: {doc.id})"
        )
        return StreamingResponse(io.BytesIO(file_bytes), media_type=doc.content_type)
        
    except Exception as e:
        write_audit_log(
            db, request, current_user.email, "DOWNLOAD_DOCUMENT", 
            current_user.tenant_id, "FAILED", f"Failed to read file from storage: {str(e)}"
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve file from storage.")

@router.delete("/{doc_id}")
def delete_document(
    doc_id: int,
    request: Request,
    current_user = Depends(RequireRole(["admin"])),
    db: Session = Depends(get_db)
):
    """Supprime un document (réservé admin, vérification du tenant)."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if doc.tenant_id != current_user.tenant_id:
        write_audit_log(
            db, request, current_user.email, "ACCESS_VIOLATION", 
            current_user.tenant_id, "DENIED", 
            f"Unauthorized attempt to delete Document {doc_id} from Tenant {doc.tenant_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Security Violation: Access to other tenant's documents is strictly prohibited."
        )
        
    try:
        storage_manager.delete_file(doc.tenant_id, doc.filename)
        
        db.delete(doc)
        db.commit()
        
        write_audit_log(
            db, request, current_user.email, "DELETE_DOCUMENT", 
            current_user.tenant_id, "SUCCESS", f"Deleted document: {doc.title} (ID: {doc.id})"
        )
        return {"status": "success", "message": f"Document {doc_id} deleted."}
        
    except Exception as e:
        write_audit_log(
            db, request, current_user.email, "DELETE_DOCUMENT", 
            current_user.tenant_id, "FAILED", f"Failed to delete: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=f"Failed to delete: {str(e)}")

@router.post("/{doc_id}/summarize")
def summarize_document(
    doc_id: int,
    request: Request,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Génère une synthèse juridique du document via Gemini."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        write_audit_log(
            db, request, current_user.email, "SUMMARIZE_DOCUMENT", 
            current_user.tenant_id, "FAILED", f"Document {doc_id} not found"
        )
        raise HTTPException(status_code=404, detail="Document not found")
        
    if doc.tenant_id != current_user.tenant_id:
        write_audit_log(
            db, request, current_user.email, "ACCESS_VIOLATION", 
            current_user.tenant_id, "DENIED", 
            f"Unauthorized attempt to summarize Document {doc_id} from Tenant {doc.tenant_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Security Violation: Access to other tenant's documents is strictly prohibited (Cross-Tenant Block)."
        )
        
    try:
        file_bytes = storage_manager.read_file(doc.tenant_id, doc.filename)
        
        text = ""
        try:
            import io
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(file_bytes))
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        except Exception as pdf_err:
            logging.error(f"Failed to parse PDF {doc.filename}: {pdf_err}")
            try:
                text = file_bytes.decode('utf-8')
            except Exception:
                raise HTTPException(status_code=400, detail=f"Failed to parse PDF text: {str(pdf_err)}")
                
        if not text.strip():
            raise HTTPException(status_code=400, detail="Le document ne contient pas de texte extractible.")
       
        prompt = (
            "Tu es un assistant juridique expert pour cabinets d'avocats. "
            "Rédige un résumé juridique clair, structuré et professionnel en français pour le document suivant. "
            "Le résumé doit être rédigé de manière concise avec des sections (par exemple: Parties impliquées, Objet, Obligations clés, Risques/Points de vigilance). "
            "Formatte la réponse en Markdown.\n\n"
            f"Contenu du document :\n{text}"
        )
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        summary = response.text     
        
        write_audit_log(
            db, request, current_user.email, "SUMMARIZE_DOCUMENT", 
            current_user.tenant_id, "SUCCESS", f"Summarized document: {doc.title} (ID: {doc.id})"
        )
        return {"doc_id": doc_id, "title": doc.title, "summary": summary}
        
    except HTTPException:
        raise
    except Exception as e:
        write_audit_log(
            db, request, current_user.email, "SUMMARIZE_DOCUMENT", 
            current_user.tenant_id, "FAILED", f"Failed to summarize: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")