/**
 * GCP GKE Terraform Configuration for LLM Crypto Trading System
 *
 * This configuration provisions:
 * - GKE cluster with 3 worker nodes
 * - VPC with custom subnets
 * - Cloud NAT for private nodes
 * - Persistent disk storage classes
 * - IAM service accounts
 * - Workload Identity
 *
 * Author: LLM Crypto Trading System Team
 * Date: 2025-10-29
 * Sprint: 3, Infrastructure Provisioning
 */

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
  }

  # Backend configuration for state management
  # Uncomment and configure when ready
  # backend "gcs" {
  #   bucket = "trader-terraform-state"
  #   prefix = "gke/terraform.tfstate"
  # }
}

# GCP Provider Configuration
provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# Data sources
data "google_client_config" "default" {}

# Local variables
locals {
  cluster_name = "${var.project_name}-${var.environment}-gke"

  common_labels = {
    project     = var.project_name
    environment = var.environment
    managed_by  = "terraform"
  }
}

# VPC Module
module "vpc" {
  source = "./modules/vpc"

  project_id   = var.project_id
  project_name = var.project_name
  environment  = var.environment
  region       = var.region

  vpc_cidr             = var.vpc_cidr
  pods_cidr            = var.pods_cidr
  services_cidr        = var.services_cidr
  enable_cloud_nat     = true
  enable_private_nodes = true

  labels = local.common_labels
}

# GKE Cluster Module
module "gke" {
  source = "./modules/gke"

  project_id   = var.project_id
  cluster_name = local.cluster_name
  region       = var.region

  network_id    = module.vpc.network_id
  subnetwork_id = module.vpc.subnetwork_id

  pods_ip_range_name     = module.vpc.pods_ip_range_name
  services_ip_range_name = module.vpc.services_ip_range_name

  # Cluster configuration
  kubernetes_version       = var.kubernetes_version
  regional                 = var.regional_cluster
  remove_default_node_pool = true

  # Node pool configuration
  node_pools = {
    general = {
      node_count       = var.node_count
      min_node_count   = var.node_min_count
      max_node_count   = var.node_max_count
      machine_type     = var.node_machine_type
      disk_size_gb     = var.node_disk_size
      disk_type        = "pd-balanced"
      preemptible      = var.use_preemptible_nodes
      auto_repair      = true
      auto_upgrade     = true
      enable_gcfs      = true

      labels = merge(
        local.common_labels,
        {
          role = "general"
        }
      )

      oauth_scopes = [
        "https://www.googleapis.com/auth/cloud-platform",
      ]
    }
  }

  # Cluster features
  enable_workload_identity     = true
  enable_shielded_nodes        = true
  enable_private_endpoint      = false
  enable_private_nodes         = true
  master_ipv4_cidr_block       = var.master_ipv4_cidr
  enable_horizontal_pod_autoscaling = true
  enable_http_load_balancing   = true
  enable_network_policy        = true

  # Monitoring and logging
  enable_cloud_logging    = true
  enable_cloud_monitoring = true
  logging_service         = "logging.googleapis.com/kubernetes"
  monitoring_service      = "monitoring.googleapis.com/kubernetes"

  labels = local.common_labels
}

# Storage Module
module "storage" {
  source = "./modules/storage"

  project_id   = var.project_id
  cluster_name = local.cluster_name

  storage_classes = var.storage_classes

  depends_on = [module.gke]
}

# Outputs
output "cluster_name" {
  description = "GKE cluster name"
  value       = module.gke.cluster_name
}

output "cluster_endpoint" {
  description = "GKE cluster endpoint"
  value       = module.gke.cluster_endpoint
  sensitive   = true
}

output "cluster_ca_certificate" {
  description = "Cluster CA certificate"
  value       = module.gke.cluster_ca_certificate
  sensitive   = true
}

output "cluster_location" {
  description = "Cluster location (region or zone)"
  value       = module.gke.cluster_location
}

output "network_name" {
  description = "VPC network name"
  value       = module.vpc.network_name
}

output "subnetwork_name" {
  description = "Subnetwork name"
  value       = module.vpc.subnetwork_name
}

output "configure_kubectl" {
  description = "Command to configure kubectl"
  value       = "gcloud container clusters get-credentials ${module.gke.cluster_name} --region ${var.region} --project ${var.project_id}"
}

output "workload_identity_pool" {
  description = "Workload Identity pool for pod IAM"
  value       = module.gke.workload_identity_pool
}
