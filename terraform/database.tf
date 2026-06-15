# Cloud SQL Instance (PostgreSQL) - Private IP only
resource "google_sql_database_instance" "postgres" {
  name             = "jurydoc-db-instance"
  database_version = "POSTGRES_15"
  region           = var.region

  # Important: Must wait for VPC Peering connection to be established
  depends_on = [google_service_networking_connection.private_vpc_connection]

  settings {
    tier = "db-f1-micro" # Small tier suitable for demonstration & cost control

    ip_configuration {
      ipv4_enabled                                  = false # NO public IP!
      private_network                               = google_compute_network.vpc.id
      enable_private_path_for_google_cloud_services = true
      ssl_mode                                      = "ENCRYPTED_ONLY" # Enforce TLS
    }

    backup_configuration {
      enabled                        = true
      start_time                     = "02:00"
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = 7
    }

    database_flags {
      name  = "log_connections"
      value = "on"
    }

    database_flags {
      name  = "log_disconnections"
      value = "on"
    }
  }
}

# Database definition
resource "google_sql_database" "db" {
  name     = "jurydoc"
  instance = google_sql_database_instance.postgres.name
}

# Admin DB User
resource "google_sql_user" "user" {
  name     = "jurydoc_admin"
  instance = google_sql_database_instance.postgres.name
  password = var.db_password
}

