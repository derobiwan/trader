/**
 * Storage Module Variables
 */

variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "storage_classes" {
  description = "Map of storage class configurations"
  type = map(object({
    type       = string
    iops       = optional(number)
    throughput = optional(number)
    encrypted  = bool
  }))
  default = {}
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
