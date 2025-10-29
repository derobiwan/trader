/**
 * VPC Module for GKE Cluster
 *
 * Creates:
 * - VPC network
 * - Subnet with secondary IP ranges for pods and services
 * - Cloud Router
 * - Cloud NAT for private nodes internet access
 * - Firewall rules
 */

# VPC Network
resource "google_compute_network" "vpc" {
  name                    = "${var.project_name}-${var.environment}-vpc"
  project                 = var.project_id
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
}

# Subnet
resource "google_compute_subnetwork" "subnet" {
  name    = "${var.project_name}-${var.environment}-subnet"
  project = var.project_id
  region  = var.region

  network       = google_compute_network.vpc.id
  ip_cidr_range = var.vpc_cidr

  # Secondary IP ranges for GKE pods and services
  secondary_ip_range {
    range_name    = "${var.project_name}-${var.environment}-pods"
    ip_cidr_range = var.pods_cidr
  }

  secondary_ip_range {
    range_name    = "${var.project_name}-${var.environment}-services"
    ip_cidr_range = var.services_cidr
  }

  private_ip_google_access = true
}

# Cloud Router for Cloud NAT
resource "google_compute_router" "router" {
  count   = var.enable_cloud_nat ? 1 : 0
  name    = "${var.project_name}-${var.environment}-router"
  project = var.project_id
  region  = var.region
  network = google_compute_network.vpc.id
}

# Cloud NAT for private nodes to access internet
resource "google_compute_router_nat" "nat" {
  count   = var.enable_cloud_nat ? 1 : 0
  name    = "${var.project_name}-${var.environment}-nat"
  project = var.project_id
  region  = var.region
  router  = google_compute_router.router[0].name

  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# Firewall Rules
resource "google_compute_firewall" "allow_internal" {
  name    = "${var.project_name}-${var.environment}-allow-internal"
  project = var.project_id
  network = google_compute_network.vpc.name

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "icmp"
  }

  source_ranges = [
    var.vpc_cidr,
    var.pods_cidr,
    var.services_cidr,
  ]

  priority = 1000
}

# Outputs
output "network_id" {
  description = "VPC network ID"
  value       = google_compute_network.vpc.id
}

output "network_name" {
  description = "VPC network name"
  value       = google_compute_network.vpc.name
}

output "network_self_link" {
  description = "VPC network self link"
  value       = google_compute_network.vpc.self_link
}

output "subnetwork_id" {
  description = "Subnetwork ID"
  value       = google_compute_subnetwork.subnet.id
}

output "subnetwork_name" {
  description = "Subnetwork name"
  value       = google_compute_subnetwork.subnet.name
}

output "subnetwork_self_link" {
  description = "Subnetwork self link"
  value       = google_compute_subnetwork.subnet.self_link
}

output "pods_ip_range_name" {
  description = "Name of the secondary IP range for pods"
  value       = "${var.project_name}-${var.environment}-pods"
}

output "services_ip_range_name" {
  description = "Name of the secondary IP range for services"
  value       = "${var.project_name}-${var.environment}-services"
}
