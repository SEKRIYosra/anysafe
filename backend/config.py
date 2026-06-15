import os
from pydantic_settings import BaseSettings

# Classe de configuration centralisee pour tout le backend.
# Les valeurs sont lues depuis les variables d'environnement,
# avec des valeurs par defaut adaptees au developpement local.
class Settings(BaseSettings):
    # Environnement courant : "dev" en local, "prod" en production
    ENV: str = os.getenv("ENV", "dev")
    # Identifiant du projet GCP
    PROJECT_ID: str = os.getenv("PROJECT_ID", "jurydoc-security-gcp")
    
    # URL de connexion a la base de donnees.
    # En local, on utilise SQLite. En production, Cloud SQL PostgreSQL.
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./jurydoc.db")
    
    # Type de stockage des fichiers : "local" pour le disque, "gcs" pour Google Cloud Storage
    STORAGE_TYPE: str = os.getenv("STORAGE_TYPE", "local")
    # Nom du bucket GCS utilise en production
    GCS_BUCKET_NAME: str = os.getenv("GCS_BUCKET_NAME", "jurydoc-documents-bucket")
    # Dossier local utilise en developpement pour stocker les fichiers
    LOCAL_STORAGE_DIR: str = os.getenv("LOCAL_STORAGE_DIR", "./local_storage")
    
    # Nom de la cle KMS pour le chiffrement CMEK (Customer-Managed Encryption Key).
    # Vide par defaut, renseigne uniquement en production via Secret Manager.
    KMS_KEY_NAME: str = os.getenv("KMS_KEY_NAME", "")
    
    # Cle secrete utilisee pour signer les jetons JWT.
    # En production, cette valeur doit etre injectee via GCP Secret Manager.
    JWT_SECRET: str = os.getenv("JWT_SECRET", "changez-cette-cle-en-production")
    # Algorithme de signature des tokens JWT
    JWT_ALGORITHM: str = str(os.getenv("JWT_ALGORITHM", "HS256"))
    # Duree de validite du token en minutes
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # Cle API Gemini pour la generation de resumes juridiques via IA
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    class Config:
        case_sensitive = True

# Instance unique de la configuration, importee dans tous les modules
settings = Settings()
