# 1. Cloud Run Service Account (Least Privilege)
resource "google_service_account" "api_sa" {
  account_id   = "jurydoc-api-sa"
  display_name = "JuryDOC API Backend Service Account"
}

# 2. Cloud KMS Setup for Customer-Managed Encryption Keys (CMEK)
resource "google_kms_key_ring" "keyring" {
  name       = "jurydoc-kms-keyring"
  location   = var.region
  depends_on = [google_project_service.services]
}

resource "google_kms_crypto_key" "gcs_key" {
  name            = "jurydoc-gcs-key"
  key_ring        = google_kms_key_ring.keyring.id
  rotation_period = "2592000s"
}

# 3. Grant GCS Service Agent rights to encrypt/decrypt using the KMS key
data "google_project" "project" {}

resource "google_kms_crypto_key_iam_binding" "gcs_kms_binding" {
  crypto_key_id = google_kms_crypto_key.gcs_key.id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"

  members = [
    "serviceAccount:service-${data.google_project.project.number}@gs-project-accounts.iam.gserviceaccount.com"
  ]
}

# 4. Secret Manager
resource "google_secret_manager_secret" "db_url_secret" {
  secret_id  = "jurydoc-db-url"
  depends_on = [google_project_service.services]

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "db_url_version" {
  secret      = google_secret_manager_secret.db_url_secret.id
  secret_data = "postgresql://jurydoc_admin:${var.db_password}@/jurydoc?host=/cloudsql/${var.project_id}:${var.region}:jurydoc-db-instance&sslmode=require"
}

resource "google_secret_manager_secret_iam_member" "api_secret_access" {
  secret_id = google_secret_manager_secret.db_url_secret.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api_sa.email}"
}

# 5. Cloud SQL Client Role for Service Account
resource "google_project_iam_member" "api_cloudsql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.api_sa.email}"
}

# 6. Cloud Run Service Deployment
resource "google_cloud_run_service" "api" {
  name     = "jurydoc-api"
  location = var.region

  template {
    spec {
      service_account_name = google_service_account.api_sa.email

      containers {
        image = "gcr.io/${var.project_id}/jurydoc-api:latest"

        env {
          name = "DATABASE_URL"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.db_url_secret.secret_id
              key  = "latest"
            }
          }
        }

        env {
          name  = "STORAGE_TYPE"
          value = "gcs"
        }

        env {
          name  = "GCS_BUCKET_NAME"
          value = var.bucket_name
        }

        env {
          name  = "KMS_KEY_NAME"
          value = google_kms_crypto_key.gcs_key.id
        }

        env {
          name = "GEMINI_API_KEY"
          value_from {
            secret_key_ref {
              name = "jurydoc-gemini-key"
              key  = "latest"
            }
          }
        }

        resources {
          limits = {
            memory = "512Mi"
            cpu    = "1000m"
          }
        }
      }
    }

    metadata {
      annotations = {
        "run.googleapis.com/vpc-access-connector" = google_vpc_access_connector.connector.name
        "run.googleapis.com/vpc-access-egress"    = "all-traffic"
        "run.googleapis.com/cloudsql-instances"   = "${var.project_id}:${var.region}:jurydoc-db-instance"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [
    google_secret_manager_secret_version.db_url_version,
    google_project_iam_member.api_cloudsql
  ]
}

# 7. Make Cloud Run public
data "google_iam_policy" "noauth" {
  binding {
    role = "roles/run.invoker"
    members = [
      "allUsers",
    ]
  }
}

resource "google_cloud_run_service_iam_policy" "noauth" {
  location    = google_cloud_run_service.api.location
  project     = google_cloud_run_service.api.project
  service     = google_cloud_run_service.api.name
  policy_data = data.google_iam_policy.noauth.policy_data
}