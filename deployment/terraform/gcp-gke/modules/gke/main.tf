/**
 * GKE Cluster Module
 *
 * Creates:
 * - GKE cluster (regional or zonal)
 * - Node pools with autoscaling
 * - Service accounts for nodes
 * - Workload Identity configuration
 * - Cluster features (logging, monitoring, network policy)
 */

# Service Account for GKE nodes
resource "google_service_account" "gke_nodes" {
  project      = var.project_id
  account_id   = "${var.cluster_name}-nodes"
  display_name = "GKE Nodes Service Account for ${var.cluster_name}"
}

# IAM roles for node service account
resource "google_project_iam_member" "gke_nodes" {
  for_each = toset([
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/monitoring.viewer",
    "roles/stackdriver.resourceMetadata.writer",
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.gke_nodes.email}"
}

# GKE Cluster
resource "google_container_cluster" "primary" {
  provider = google-beta
  project  = var.project_id
  name     = var.cluster_name
  location = var.regional ? var.region : var.zones[0]

  # Kubernetes version
  min_master_version = var.kubernetes_version

  # Network configuration
  network    = var.network_id
  subnetwork = var.subnetwork_id

  # IP allocation policy for pods and services
  ip_allocation_policy {
    cluster_secondary_range_name  = var.pods_ip_range_name
    services_secondary_range_name = var.services_ip_range_name
  }

  # Private cluster configuration
  private_cluster_config {
    enable_private_nodes    = var.enable_private_nodes
    enable_private_endpoint = var.enable_private_endpoint
    master_ipv4_cidr_block  = var.master_ipv4_cidr_block
  }

  # Master authorized networks
  dynamic "master_authorized_networks_config" {
    for_each = length(var.master_authorized_networks) > 0 ? [1] : []
    content {
      dynamic "cidr_blocks" {
        for_each = var.master_authorized_networks
        content {
          cidr_block   = cidr_blocks.value.cidr_block
          display_name = cidr_blocks.value.display_name
        }
      }
    }
  }

  # Remove default node pool
  remove_default_node_pool = var.remove_default_node_pool
  initial_node_count       = var.remove_default_node_pool ? 1 : var.initial_node_count

  # Workload Identity
  workload_identity_config {
    workload_pool = var.enable_workload_identity ? "${var.project_id}.svc.id.goog" : null
  }

  # Addons
  addons_config {
    http_load_balancing {
      disabled = !var.enable_http_load_balancing
    }

    horizontal_pod_autoscaling {
      disabled = !var.enable_horizontal_pod_autoscaling
    }

    network_policy_config {
      disabled = !var.enable_network_policy
    }

    gcp_filestore_csi_driver_config {
      enabled = false
    }

    gce_persistent_disk_csi_driver_config {
      enabled = true
    }
  }

  # Network policy
  network_policy {
    enabled  = var.enable_network_policy
    provider = var.enable_network_policy ? "PROVIDER_UNSPECIFIED" : null
  }

  # Logging and monitoring
  logging_service    = var.logging_service
  monitoring_service = var.monitoring_service

  # Maintenance policy
  maintenance_policy {
    daily_maintenance_window {
      start_time = "03:00"
    }
  }

  # Resource labels
  resource_labels = var.labels

  # Lifecycle
  lifecycle {
    ignore_changes = [
      initial_node_count,
      node_config,
    ]
  }

  # Enable shielded nodes
  enable_shielded_nodes = var.enable_shielded_nodes

  # Release channel
  release_channel {
    channel = var.release_channel
  }
}

# Node Pools
resource "google_container_node_pool" "pools" {
  for_each = var.node_pools

  provider = google-beta
  project  = var.project_id
  name     = each.key
  location = var.regional ? var.region : var.zones[0]
  cluster  = google_container_cluster.primary.name

  # Node count configuration
  initial_node_count = each.value.node_count

  # Autoscaling
  autoscaling {
    min_node_count = each.value.min_node_count
    max_node_count = each.value.max_node_count
  }

  # Management
  management {
    auto_repair  = each.value.auto_repair
    auto_upgrade = each.value.auto_upgrade
  }

  # Node configuration
  node_config {
    machine_type = each.value.machine_type
    disk_size_gb = each.value.disk_size_gb
    disk_type    = each.value.disk_type
    preemptible  = each.value.preemptible

    # Service account
    service_account = google_service_account.gke_nodes.email

    # OAuth scopes
    oauth_scopes = each.value.oauth_scopes

    # Labels
    labels = each.value.labels

    # Metadata
    metadata = {
      disable-legacy-endpoints = "true"
    }

    # Workload Identity
    workload_metadata_config {
      mode = var.enable_workload_identity ? "GKE_METADATA" : "GCE_METADATA"
    }

    # Shielded instance config
    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }

    # GCFS (Google Container File System)
    gcfs_config {
      enabled = each.value.enable_gcfs
    }
  }

  # Lifecycle
  lifecycle {
    ignore_changes = [
      initial_node_count,
    ]
  }
}

# Outputs
output "cluster_id" {
  description = "GKE cluster ID"
  value       = google_container_cluster.primary.id
}

output "cluster_name" {
  description = "GKE cluster name"
  value       = google_container_cluster.primary.name
}

output "cluster_endpoint" {
  description = "GKE cluster endpoint"
  value       = google_container_cluster.primary.endpoint
}

output "cluster_ca_certificate" {
  description = "Cluster CA certificate"
  value       = google_container_cluster.primary.master_auth[0].cluster_ca_certificate
}

output "cluster_location" {
  description = "Cluster location (region or zone)"
  value       = google_container_cluster.primary.location
}

output "cluster_master_version" {
  description = "Kubernetes master version"
  value       = google_container_cluster.primary.master_version
}

output "workload_identity_pool" {
  description = "Workload Identity pool"
  value       = var.enable_workload_identity ? "${var.project_id}.svc.id.goog" : null
}

output "node_service_account" {
  description = "Service account used by nodes"
  value       = google_service_account.gke_nodes.email
}

output "node_pools" {
  description = "Node pool names"
  value       = keys(var.node_pools)
}
