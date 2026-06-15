variable "project_id" {
  description = "The GCP Project ID to deploy resources in"
  type        = string
  default     = "any-safe-episen"
}

variable "region" {
  description = "GCP Region for deployment (Paris region recommended for legal compliance)"
  type        = string
  default     = "europe-west9"
}

variable "db_password" {
  description = "Database administrator password (marked sensitive to prevent CI/CD exposure)"
  type        = string
  sensitive   = true
  default     = "AnySafe2026!Secure"
}

variable "bucket_name" {
  description = "Unique name for the Google Cloud Storage bucket storing legal case files"
  type        = string
  default     = "anysafe-documents-episen"
}
