/**
 * VPC Module Variables
 */

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for VPC subnet"
  type        = string
}

variable "pods_cidr" {
  description = "CIDR block for pods secondary IP range"
  type        = string
}

variable "services_cidr" {
  description = "CIDR block for services secondary IP range"
  type        = string
}

variable "enable_cloud_nat" {
  description = "Enable Cloud NAT for private nodes"
  type        = bool
  default     = true
}

variable "enable_private_nodes" {
  description = "Enable private nodes (no external IPs)"
  type        = bool
  default     = true
}

variable "labels" {
  description = "Labels to apply to resources"
  type        = map(string)
  default     = {}
}
