# Staging Environment Configuration
# Use this for testing and validation before production deployment

# General
project_name = "llm-crypto-trader"
environment  = "staging"
owner        = "devops@example.com"

# AWS
aws_region = "us-east-1"

# VPC
vpc_cidr             = "10.0.0.0/16"
public_subnet_cidrs  = ["10.0.1.0/24", "10.0.2.0/24"]
private_subnet_cidrs = ["10.0.10.0/24", "10.0.20.0/24"]

# EKS
cluster_version = "1.28"

# Node Configuration (Smaller for staging to reduce costs)
node_instance_types = ["t3.medium"]  # 2 vCPU, 4 GB RAM
node_desired_size   = 2              # Smaller cluster for staging
node_min_size       = 1
node_max_size       = 3
node_disk_size      = 30             # Smaller disk for staging

# Monitoring
enable_cloudwatch_logs = true
cluster_log_types      = ["api", "audit"]  # Reduced logging for cost

# Storage
enable_ebs_csi_driver = true

# Security
allowed_cidr_blocks = []  # Empty = VPC only access

# Cost Optimization
enable_spot_instances = true  # Use spot for staging to save costs

# Backup
enable_snapshot_lifecycle = false  # Disable automated snapshots in staging
snapshot_retention_days   = 7

# Tags
additional_tags = {
  CostCenter = "engineering"
  Purpose    = "staging"
  AutoShutdown = "enabled"  # Can be used for cost optimization scripts
}
