# 1. Cloud Storage Bucket for legal case files
resource "google_storage_bucket" "documents" {
  name                        = var.bucket_name
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  force_destroy               = false

  # Mandatory Control: Prevent public access to the bucket
  public_access_prevention = "enforced"

  # Versioning for data integrity & backups
  versioning {
    enabled = true
  }

  # Customer-Managed Encryption Key (CMEK) for data at rest
  encryption {
    default_kms_key_name = google_kms_crypto_key.gcs_key.id
  }

  # Lifecycle policy to automatically archive older legal files if needed
  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  depends_on = [google_kms_crypto_key_iam_binding.gcs_kms_binding]
}

# 2. IAM Binding: Enforce least-privilege access
# Allow our Cloud Run backend service account to manage documents inside GCS bucket
resource "google_storage_bucket_iam_member" "api_storage_access" {
  bucket = google_storage_bucket.documents.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.api_sa.email}"
}
