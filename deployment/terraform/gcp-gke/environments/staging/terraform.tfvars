# Staging Environment Configuration for GCP GKE
# Cost-optimized configuration for testing and validation

# GCP Project (MUST BE SET)
project_id = "your-gcp-project-id"  # Replace with your actual project ID

# General
project_name = "llm-crypto-trader"
environment  = "staging"

# Region
region = "us-central1"
zones  = ["us-central1-a", "us-central1-b", "us-central1-c"]

# Network
vpc_cidr      = "10.0.0.0/20"
pods_cidr     = "10.4.0.0/14"
services_cidr = "10.8.0.0/20"
master_ipv4_cidr = "172.16.0.0/28"

# Cluster
kubernetes_version = "1.28"
regional_cluster   = false  # Zonal cluster for cost savings

# Node Configuration (Smaller for staging)
node_machine_type      = "e2-standard-2"  # 2 vCPU, 8 GB RAM
node_count             = 2                # Total 2 nodes in zone
node_min_count         = 1
node_max_count         = 3
node_disk_size         = 30               # Smaller disk
use_preemptible_nodes  = true             # Use spot instances (~70% savings)

# Monitoring
enable_cloud_logging    = true
enable_cloud_monitoring = true

# Security
enable_workload_identity = true
enable_shielded_nodes    = true

# No authorized networks = restrict to private IPs only
master_authorized_networks = []

# Cost Optimization
enable_backup_agent = false  # Disable backups in staging

# Labels
additional_labels = {
  cost_center  = "engineering"
  purpose      = "staging"
  auto_shutdown = "enabled"  # Can be used for cost optimization automation
}
