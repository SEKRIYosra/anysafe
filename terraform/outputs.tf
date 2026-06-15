output "vpc_name" {
  description = "The name of the VPC network"
  value       = google_compute_network.vpc.name
}

output "cloud_sql_private_ip" {
  description = "The private IP address of the Cloud SQL instance"
  value       = google_sql_database_instance.postgres.private_ip_address
}

output "gcs_bucket_url" {
  description = "The GCS Bucket URI"
  value       = google_storage_bucket.documents.url
}

output "cloud_run_service_url" {
  description = "The deployment URL of the JuryDOC API on Cloud Run"
  value       = google_cloud_run_service.api.status[0].url
}