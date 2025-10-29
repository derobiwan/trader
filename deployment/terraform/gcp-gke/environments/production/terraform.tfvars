# Production Environment Configuration for GCP GKE
# High availability, performance-optimized configuration

# GCP Project (MUST BE SET)
project_id = "your-gcp-project-id"  # Replace with your actual project ID

# General
project_name = "llm-crypto-trader"
environment  = "production"

# Region
region = "us-central1"
zones  = ["us-central1-a", "us-central1-b", "us-central1-c"]

# Network (Different CIDR from staging)
vpc_cidr      = "10.1.0.0/20"
pods_cidr     = "10.5.0.0/14"
services_cidr = "10.9.0.0/20"
master_ipv4_cidr = "172.16.0.16/28"

# Cluster
kubernetes_version = "1.28"
regional_cluster   = true  # Regional for high availability

# Node Configuration (Production-ready)
node_machine_type      = "e2-standard-4"  # 4 vCPU, 16 GB RAM per node
node_count             = 1                # 1 node per zone = 3 total (regional)
node_min_count         = 1                # Minimum 3 nodes (1 per zone)
node_max_count         = 2                # Maximum 6 nodes (2 per zone)
node_disk_size         = 50               # Adequate storage
use_preemptible_nodes  = false            # Use regular instances for stability

# Monitoring
enable_cloud_logging    = true
enable_cloud_monitoring = true

# Security
enable_workload_identity = true
enable_shielded_nodes    = true

# No authorized networks = restrict to private IPs only
# Add your office/VPN IPs if you need direct kubectl access
master_authorized_networks = [
  # {
  #   cidr_block   = "203.0.113.0/24"
  #   display_name = "Office Network"
  # }
]

# Backup
enable_backup_agent = true  # Enable backups for production

# Labels
additional_labels = {
  cost_center       = "trading-operations"
  purpose           = "production"
  compliance        = "required"
  backup_policy     = "daily"
  disaster_recovery = "enabled"
}
