# Production Environment Configuration
# High availability, performance-optimized configuration

# General
project_name = "llm-crypto-trader"
environment  = "production"
owner        = "devops@example.com"

# AWS
aws_region = "us-east-1"

# VPC
vpc_cidr             = "10.1.0.0/16"  # Different CIDR from staging
public_subnet_cidrs  = ["10.1.1.0/24", "10.1.2.0/24"]
private_subnet_cidrs = ["10.1.10.0/24", "10.1.20.0/24"]

# EKS
cluster_version = "1.28"

# Node Configuration (Production-ready)
node_instance_types = ["t3.large"]  # 2 vCPU, 8 GB RAM per node
node_desired_size   = 3             # 3 nodes for high availability
node_min_size       = 3             # Maintain 3 nodes minimum
node_max_size       = 6             # Allow scaling to 6 nodes
node_disk_size      = 50            # Adequate storage

# Monitoring
enable_cloudwatch_logs = true
cluster_log_types      = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

# Storage
enable_ebs_csi_driver = true

# Security
allowed_cidr_blocks = []  # Empty = VPC only access

# Cost Optimization
enable_spot_instances = false  # Use on-demand for production stability

# Backup
enable_snapshot_lifecycle = true
snapshot_retention_days   = 30

# Tags
additional_tags = {
  CostCenter    = "trading-operations"
  Purpose       = "production"
  Compliance    = "required"
  BackupPolicy  = "daily"
  DisasterRecovery = "enabled"
}
