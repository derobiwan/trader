/**
 * GKE Module Variables
 */

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "cluster_name" {
  description = "Name of the GKE cluster"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
}

variable "zones" {
  description = "GCP zones for zonal cluster"
  type        = list(string)
  default     = []
}

variable "regional" {
  description = "Create regional cluster (true) or zonal cluster (false)"
  type        = bool
  default     = true
}

variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
}

variable "network_id" {
  description = "VPC network ID"
  type        = string
}

variable "subnetwork_id" {
  description = "Subnetwork ID"
  type        = string
}

variable "pods_ip_range_name" {
  description = "Name of secondary IP range for pods"
  type        = string
}

variable "services_ip_range_name" {
  description = "Name of secondary IP range for services"
  type        = string
}

variable "enable_private_nodes" {
  description = "Enable private nodes (no external IPs)"
  type        = bool
  default     = true
}

variable "enable_private_endpoint" {
  description = "Enable private endpoint for GKE master"
  type        = bool
  default     = false
}

variable "master_ipv4_cidr_block" {
  description = "CIDR block for GKE master"
  type        = string
}

variable "master_authorized_networks" {
  description = "Networks allowed to access GKE master"
  type = list(object({
    cidr_block   = string
    display_name = string
  }))
  default = []
}

variable "remove_default_node_pool" {
  description = "Remove default node pool after cluster creation"
  type        = bool
  default     = true
}

variable "initial_node_count" {
  description = "Initial node count for default pool"
  type        = number
  default     = 1
}

variable "node_pools" {
  description = "Map of node pool configurations"
  type = map(object({
    node_count       = number
    min_node_count   = number
    max_node_count   = number
    machine_type     = string
    disk_size_gb     = number
    disk_type        = string
    preemptible      = bool
    auto_repair      = bool
    auto_upgrade     = bool
    enable_gcfs      = bool
    labels           = map(string)
    oauth_scopes     = list(string)
  }))
}

variable "enable_workload_identity" {
  description = "Enable Workload Identity"
  type        = bool
  default     = true
}

variable "enable_shielded_nodes" {
  description = "Enable Shielded GKE Nodes"
  type        = bool
  default     = true
}

variable "enable_http_load_balancing" {
  description = "Enable HTTP load balancing addon"
  type        = bool
  default     = true
}

variable "enable_horizontal_pod_autoscaling" {
  description = "Enable horizontal pod autoscaling addon"
  type        = bool
  default     = true
}

variable "enable_network_policy" {
  description = "Enable network policy addon"
  type        = bool
  default     = true
}

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

variable "logging_service" {
  description = "Logging service"
  type        = string
  default     = "logging.googleapis.com/kubernetes"
}

variable "monitoring_service" {
  description = "Monitoring service"
  type        = string
  default     = "monitoring.googleapis.com/kubernetes"
}

variable "release_channel" {
  description = "Release channel (RAPID, REGULAR, STABLE)"
  type        = string
  default     = "REGULAR"
}

variable "labels" {
  description = "Labels to apply to resources"
  type        = map(string)
  default     = {}
}
