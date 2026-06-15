# 1. Custom VPC Network
resource "google_compute_network" "vpc" {
  name                    = "jurydoc-vpc"
  auto_create_subnetworks = false
  depends_on              = [google_project_service.services]
}

# 2. Private Subnet for Internal Assets
resource "google_compute_subnetwork" "private_subnet" {
  name                     = "jurydoc-private-subnet"
  ip_cidr_range            = "10.0.1.0/24"
  region                   = var.region
  network                  = google_compute_network.vpc.id
  private_ip_google_access = true
}

# 3. Reserved Private IP Block for Cloud SQL / Private Peering
resource "google_compute_global_address" "private_ip_alloc" {
  name          = "jurydoc-private-ip-alloc"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc.id
}

# 4. Establish Private Services Connection for Peering
resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_alloc.name]
}

# 5. Serverless VPC Access Connector (For Cloud Run to reach private resources)
resource "google_vpc_access_connector" "connector" {
  name          = "jurydoc-vpc-connector"
  region        = var.region
  network       = google_compute_network.vpc.name
  ip_cidr_range = "10.8.0.0/28" # Must not overlap with other subnets
  min_instances = 2
  max_instances = 10
  depends_on    = [google_project_service.services]
}

# 6. Egress Control: Cloud Router + NAT Gateway (No direct public IPs on compute)
resource "google_compute_router" "router" {
  name    = "jurydoc-router"
  region  = var.region
  network = google_compute_network.vpc.id
}

resource "google_compute_router_nat" "nat" {
  name                               = "jurydoc-nat"
  router                             = google_compute_router.router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}

# 7. Internal Network Segments: Firewall rules (Deny by default)
resource "google_compute_firewall" "allow_internal" {
  name    = "jurydoc-allow-internal"
  network = google_compute_network.vpc.name

  allow {
    protocol = "tcp"
    ports    = ["5432"] # Only SQL internal communication allowed
  }

  source_ranges = ["10.0.1.0/24", "10.8.0.0/28"]
  target_tags   = ["db"]
}
