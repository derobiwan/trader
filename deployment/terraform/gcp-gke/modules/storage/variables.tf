/**
 * Storage Module Variables
 */

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "cluster_name" {
  description = "Name of the GKE cluster"
  type        = string
}

variable "storage_classes" {
  description = "Map of storage class configurations"
  type = map(object({
    type        = string
    replication = string
    provisioner = string
  }))
  default = {}
}
