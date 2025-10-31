/**
 * Terraform Variables for GCP GKE Infrastructure
 *
 * Define all input variables for customizing the infrastructure.
 * Override defaults using terraform.tfvars or -var flags.
 */

# General Configuration
variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "llm-crypto-trader"
}

variable "environment" {
  description = "Environment name (staging, production)"
  type        = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Environment must be either 'staging' or 'production'."
  }
}

# GCP Configuration
variable "region" {
  description = "GCP region for all resources"
  type        = string
  default     = "us-central1"
}

variable "zones" {
  description = "GCP zones for multi-zonal cluster (optional, for zonal clusters)"
  type        = list(string)
  default     = ["us-central1-a", "us-central1-b", "us-central1-c"]
}

# Network Configuration
variable "vpc_cidr" {
  description = "CIDR block for VPC subnet"
  type        = string
  default     = "10.0.0.0/20"
}

variable "pods_cidr" {
  description = "CIDR block for pods secondary IP range"
  type        = string
  default     = "10.4.0.0/14"
}

variable "services_cidr" {
  description = "CIDR block for services secondary IP range"
  type        = string
  default     = "10.8.0.0/20"
}

variable "master_ipv4_cidr" {
  description = "CIDR block for GKE master (private endpoint)"
  type        = string
  default     = "172.16.0.0/28"
}

# GKE Cluster Configuration
variable "kubernetes_version" {
  description = "Kubernetes version for GKE cluster"
  type        = string
  default     = "1.28"
}

variable "regional_cluster" {
  description = "Create regional cluster (true) or zonal cluster (false)"
  type        = bool
  default     = true
}

# Node Pool Configuration
variable "node_machine_type" {
  description = "Machine type for worker nodes"
  type        = string
  default     = "e2-standard-4"  # 4 vCPU, 16 GB RAM
}

variable "node_count" {
  description = "Number of nodes per zone (regional) or total (zonal)"
  type        = number
  default     = 1
}

variable "node_min_count" {
  description = "Minimum number of nodes for autoscaling"
  type        = number
  default     = 1
}

variable "node_max_count" {
  description = "Maximum number of nodes for autoscaling"
  type        = number
  default     = 3
}

variable "node_disk_size" {
  description = "Disk size in GB for worker nodes"
  type        = number
  default     = 50
}

variable "use_preemptible_nodes" {
  description = "Use preemptible (spot) nodes for cost savings"
  type        = bool
  default     = false
}

# Storage Configuration
variable "storage_classes" {
  description = "Storage class configurations"
  type = map(object({
    type           = string
    replication    = string
    provisioner    = string
  }))
  default = {
    balanced = {
      type        = "pd-balanced"
      replication = "none"
      provisioner = "pd.csi.storage.gke.io"
    }
    ssd = {
      type        = "pd-ssd"
      replication = "none"
      provisioner = "pd.csi.storage.gke.io"
    }
  }
}

# Monitoring Configuration
variable "enable_cloud_logging" {
  description = "Enable Cloud Logging"
  type        = bool
  default     = true
}

variable "enable_cloud_monitoring" {
  description = "Enable Cloud Monitoring"
  type        = bool
  default     = true
}

# Security Configuration
variable "enable_workload_identity" {
  description = "Enable Workload Identity for pod-level IAM"
  type        = bool
  default     = true
}

variable "enable_shielded_nodes" {
  description = "Enable Shielded GKE Nodes"
  type        = bool
  default     = true
}

variable "master_authorized_networks" {
  description = "CIDR blocks allowed to access GKE master"
  type = list(object({
    cidr_block   = string
    display_name = string
  }))
  default = []
}

# Backup Configuration
variable "enable_backup_agent" {
  description = "Enable GKE Backup for Workloads"
  type        = bool
  default     = false
}

# Labels
variable "additional_labels" {
  description = "Additional labels to apply to all resources"
  type        = map(string)
  default     = {}
}
