import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ENV: str = os.getenv("ENV", "dev")
    PROJECT_ID: str = os.getenv("PROJECT_ID", "jurydoc-security-gcp")
    
    # Database configuration
    # For local dev, defaults to SQLite. For production, Cloud SQL PostgreSQL.
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./jurydoc.db")
    
    # Storage configuration ("local" or "gcs")
    STORAGE_TYPE: str = os.getenv("STORAGE_TYPE", "local")
    GCS_BUCKET_NAME: str = os.getenv("GCS_BUCKET_NAME", "jurydoc-documents-bucket")
    LOCAL_STORAGE_DIR: str = os.getenv("LOCAL_STORAGE_DIR", "./local_storage")
    
    # KMS Configuration for CMEK simulation or real KMS usage
    KMS_KEY_NAME: str = os.getenv("KMS_KEY_NAME", "")
    
    # JWT security settings
    JWT_SECRET: str = os.getenv("JWT_SECRET", "changez-cette-cle-en-production")
    JWT_ALGORITHM: str = str(os.getenv("JWT_ALGORITHM", "HS256"))
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # Gemini configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    class Config:
        case_sensitive = True

settings = Settings()
