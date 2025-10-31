/**
 * Storage Module for GKE
 *
 * Creates:
 * - Kubernetes StorageClasses for different storage types
 * - Persistent Disk configurations
 */

terraform {
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
  }
}

# Balanced Persistent Disk Storage Class (default)
resource "kubernetes_storage_class_v1" "balanced" {
  metadata {
    name = "pd-balanced"
    annotations = {
      "storageclass.kubernetes.io/is-default-class" = "true"
    }
  }

  storage_provisioner = "pd.csi.storage.gke.io"
  volume_binding_mode = "WaitForFirstConsumer"
  allow_volume_expansion = true

  parameters = {
    type = "pd-balanced"
    replication-type = "none"
  }

  reclaim_policy = "Retain"
}

# SSD Persistent Disk Storage Class (high-performance)
resource "kubernetes_storage_class_v1" "ssd" {
  metadata {
    name = "pd-ssd-performance"
  }

  storage_provisioner = "pd.csi.storage.gke.io"
  volume_binding_mode = "WaitForFirstConsumer"
  allow_volume_expansion = true

  parameters = {
    type = "pd-ssd"
    replication-type = "none"
  }

  reclaim_policy = "Retain"
}

# Standard Persistent Disk Storage Class (cost-optimized)
resource "kubernetes_storage_class_v1" "standard" {
  metadata {
    name = "pd-standard-economy"
  }

  storage_provisioner = "pd.csi.storage.gke.io"
  volume_binding_mode = "WaitForFirstConsumer"
  allow_volume_expansion = true

  parameters = {
    type = "pd-standard"
    replication-type = "none"
  }

  reclaim_policy = "Retain"
}

# Regional Persistent Disk Storage Class (high-availability)
resource "kubernetes_storage_class_v1" "regional_balanced" {
  metadata {
    name = "pd-regional-balanced"
  }

  storage_provisioner = "pd.csi.storage.gke.io"
  volume_binding_mode = "WaitForFirstConsumer"
  allow_volume_expansion = true

  parameters = {
    type = "pd-balanced"
    replication-type = "regional-pd"
  }

  reclaim_policy = "Retain"
}

# Outputs
output "storage_class_names" {
  description = "Names of created storage classes"
  value = {
    default      = kubernetes_storage_class_v1.balanced.metadata[0].name
    performance  = kubernetes_storage_class_v1.ssd.metadata[0].name
    economy      = kubernetes_storage_class_v1.standard.metadata[0].name
    regional     = kubernetes_storage_class_v1.regional_balanced.metadata[0].name
  }
}
