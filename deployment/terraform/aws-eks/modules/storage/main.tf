/**
 * Storage Module for EKS
 *
 * Creates:
 * - Kubernetes StorageClasses for different storage types
 * - Backup policies
 * - Volume snapshot classes
 */

terraform {
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
  }
}

# GP3 Storage Class (default, cost-optimized)
resource "kubernetes_storage_class_v1" "gp3" {
  metadata {
    name = "gp3"
    annotations = {
      "storageclass.kubernetes.io/is-default-class" = "true"
    }
  }

  storage_provisioner = "ebs.csi.aws.com"
  volume_binding_mode = "WaitForFirstConsumer"
  allow_volume_expansion = true

  parameters = {
    type      = "gp3"
    encrypted = "true"
    iops      = "3000"
    throughput = "125"
  }

  reclaim_policy = "Retain"
}

# IO1 Storage Class (high-performance, database workloads)
resource "kubernetes_storage_class_v1" "io1" {
  metadata {
    name = "io1-high-performance"
  }

  storage_provisioner = "ebs.csi.aws.com"
  volume_binding_mode = "WaitForFirstConsumer"
  allow_volume_expansion = true

  parameters = {
    type      = "io1"
    encrypted = "true"
    iopsPerGB = "50"
  }

  reclaim_policy = "Retain"
}

# GP2 Storage Class (legacy, for compatibility)
resource "kubernetes_storage_class_v1" "gp2" {
  metadata {
    name = "gp2-legacy"
  }

  storage_provisioner = "ebs.csi.aws.com"
  volume_binding_mode = "WaitForFirstConsumer"
  allow_volume_expansion = true

  parameters = {
    type      = "gp2"
    encrypted = "true"
  }

  reclaim_policy = "Retain"
}

# Volume Snapshot Class
resource "kubernetes_storage_class_v1" "snapshot" {
  metadata {
    name = "ebs-snapshot"
  }

  storage_provisioner = "ebs.csi.aws.com"

  parameters = {
    encrypted = "true"
  }
}

# Outputs
output "storage_class_names" {
  description = "Names of created storage classes"
  value = {
    default  = kubernetes_storage_class_v1.gp3.metadata[0].name
    performance = kubernetes_storage_class_v1.io1.metadata[0].name
    legacy   = kubernetes_storage_class_v1.gp2.metadata[0].name
  }
}
