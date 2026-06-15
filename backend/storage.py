# Gestionnaire de stockage des fichiers.
# Supporte deux modes :
# - "local" : stockage sur le disque du serveur (developpement)
# - "gcs" : stockage sur Google Cloud Storage (production)
# Les fichiers sont organises par tenant (cabinet) pour garantir l'isolation.

import os
import logging
from fastapi import UploadFile
from backend.config import settings


class StorageManager:
    """Classe qui gere le stockage des fichiers de facon transparente.
    L'appelant n'a pas besoin de savoir si les fichiers sont stockes
    en local ou sur GCS, l'interface est la meme."""

    def __init__(self):
        self.storage_type = settings.STORAGE_TYPE
        self.local_dir = settings.LOCAL_STORAGE_DIR
        self.bucket_name = settings.GCS_BUCKET_NAME
        
        if self.storage_type == "local":
            # En mode local, on cree le dossier de stockage s'il n'existe pas
            os.makedirs(self.local_dir, exist_ok=True)
            logging.info(f"Local storage initialized at: {self.local_dir}")
        else:
            # En mode GCS, on initialise le client Google Cloud Storage
            try:
                from google.cloud import storage
                self.gcs_client = storage.Client()
                logging.info(f"GCS client initialized. Target bucket: {self.bucket_name}")
            except Exception as e:
                # En cas d'echec (pas de credentials par exemple),
                # on bascule automatiquement sur le stockage local
                logging.error(f"Failed to initialize GCS client: {e}. Falling back to local storage.")
                self.storage_type = "local"
                os.makedirs(self.local_dir, exist_ok=True)

    def save_file(self, tenant_id: str, filename: str, file_content: bytes) -> str:
        """Enregistre un fichier dans le stockage, isole par cabinet (tenant).
        Retourne le chemin ou l'URI du fichier enregistre."""

        if self.storage_type == "local":
            # Chaque tenant a son propre sous-dossier
            tenant_dir = os.path.join(self.local_dir, tenant_id)
            os.makedirs(tenant_dir, exist_ok=True)
            file_path = os.path.join(tenant_dir, filename)
            with open(file_path, "wb") as f:
                f.write(file_content)
            return file_path
        else:
            # Upload vers Google Cloud Storage avec chiffrement CMEK si configure
            from google.cloud import storage
            bucket = self.gcs_client.bucket(self.bucket_name)
            blob_path = f"{tenant_id}/{filename}"
            blob = bucket.blob(blob_path)
            
            # Si une cle KMS est configuree, on l'utilise pour le chiffrement
            if settings.KMS_KEY_NAME:
                blob.kms_key_name = settings.KMS_KEY_NAME
                logging.info(f"Uploading file with CMEK key: {settings.KMS_KEY_NAME}")
            
            blob.upload_from_string(file_content)
            return f"gs://{self.bucket_name}/{blob_path}"

    def read_file(self, tenant_id: str, filename: str) -> bytes:
        """Lit le contenu d'un fichier depuis le stockage.
        Leve une erreur si le fichier n'existe pas."""

        if self.storage_type == "local":
            file_path = os.path.join(self.local_dir, tenant_id, filename)
            if not os.path.exists(file_path):
                raise FileNotFoundError("File not found in local storage.")
            with open(file_path, "rb") as f:
                return f.read()
        else:
            bucket = self.gcs_client.bucket(self.bucket_name)
            blob_path = f"{tenant_id}/{filename}"
            blob = bucket.blob(blob_path)
            if not blob.exists():
                raise FileNotFoundError("File not found in GCS bucket.")
            return blob.download_as_bytes()

    def delete_file(self, tenant_id: str, filename: str):
        """Supprime un fichier du stockage.
        Ne leve pas d'erreur si le fichier n'existe pas."""

        if self.storage_type == "local":
            file_path = os.path.join(self.local_dir, tenant_id, filename)
            if os.path.exists(file_path):
                os.remove(file_path)
        else:
            bucket = self.gcs_client.bucket(self.bucket_name)
            blob_path = f"{tenant_id}/{filename}"
            blob = bucket.blob(blob_path)
            if blob.exists():
                blob.delete()

# Instance unique du gestionnaire de stockage, utilisee dans toute l'application
storage_manager = StorageManager()
