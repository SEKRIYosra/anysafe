import os
import logging
from fastapi import UploadFile
from backend.config import settings

class StorageManager:
    def __init__(self):
        self.storage_type = settings.STORAGE_TYPE
        self.local_dir = settings.LOCAL_STORAGE_DIR
        self.bucket_name = settings.GCS_BUCKET_NAME
        
        if self.storage_type == "local":
            os.makedirs(self.local_dir, exist_ok=True)
            logging.info(f"Local storage initialized at: {self.local_dir}")
        else:
            try:
                from google.cloud import storage
                self.gcs_client = storage.Client()
                logging.info(f"GCS client initialized. Target bucket: {self.bucket_name}")
            except Exception as e:
                logging.error(f"Failed to initialize GCS client: {e}. Falling back to local storage.")
                self.storage_type = "local"
                os.makedirs(self.local_dir, exist_ok=True)

    def save_file(self, tenant_id: str, filename: str, file_content: bytes) -> str:
        """Enregistrement d'un fichier cloisonné par tenant."""
        if self.storage_type == "local":
            tenant_dir = os.path.join(self.local_dir, tenant_id)
            os.makedirs(tenant_dir, exist_ok=True)
            file_path = os.path.join(tenant_dir, filename)
            with open(file_path, "wb") as f:
                f.write(file_content)
            return file_path
        else:
            # GCP Cloud Storage
            from google.cloud import storage
            bucket = self.gcs_client.bucket(self.bucket_name)
            blob_path = f"{tenant_id}/{filename}"
            blob = bucket.blob(blob_path)
            
            if settings.KMS_KEY_NAME:
                blob.kms_key_name = settings.KMS_KEY_NAME
                logging.info(f"Uploading file with CMEK key: {settings.KMS_KEY_NAME}")
            
            blob.upload_from_string(file_content)
            return f"gs://{self.bucket_name}/{blob_path}"

    def read_file(self, tenant_id: str, filename: str) -> bytes:
        """Lecture d'un fichier."""
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
        """Suppression d'un fichier."""
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

storage_manager = StorageManager()
