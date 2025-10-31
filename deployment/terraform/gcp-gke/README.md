# GCP GKE Infrastructure Terraform Configuration

Infrastructure-as-Code for deploying the LLM Crypto Trading System on Google Kubernetes Engine (GKE).

## 📋 Quick Start

```bash
# 1. Install prerequisites
brew install terraform gcloud kubectl

# 2. Authenticate with GCP
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# 3. Deploy staging
cd deployment/terraform/gcp-gke
./setup.sh staging

# Takes ~10-15 minutes, costs ~$140/month
```

## 🏗️ Architecture

- **VPC**: Custom network with secondary ranges for pods and services
- **GKE Cluster**: Regional (prod) or zonal (staging) Kubernetes cluster
- **Node Pools**: Auto-scaling compute instances
- **Cloud NAT**: Private node internet access
- **Storage**: Persistent Disk CSI driver with multiple storage classes
- **Security**: Workload Identity, Shielded Nodes, private nodes

### Infrastructure Components

| Component | Staging | Production |
|-----------|---------|------------|
| **Cluster Type** | Zonal | Regional |
| **Node Type** | e2-standard-2 | e2-standard-4 |
| **Node Count** | 2 | 3 (1 per zone) |
| **Disk Size** | 30GB | 50GB |
| **Preemptible** | Yes (65% savings) | No |
| **Estimated Cost** | ~$140/mo | ~$290/mo |

## 🚀 Deployment

### Prerequisites

```bash
# Install tools
brew install terraform  # >= 1.6.0
brew install google-cloud-sdk
brew install kubectl

# Authenticate
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Verify
terraform --version
gcloud --version
kubectl version --client
```

### Deploy Staging

```bash
# Copy configuration
cp environments/staging/terraform.tfvars .

# Edit if needed (project_id will be auto-filled)
vi terraform.tfvars

# Deploy
./setup.sh staging
```

### Deploy Production

```bash
cp environments/production/terraform.tfvars .
./setup.sh production
```

### Manual Deployment

```bash
# Initialize
terraform init

# Plan
terraform plan -out=tfplan

# Apply
terraform apply tfplan

# Configure kubectl
gcloud container clusters get-credentials \
  llm-crypto-trader-staging-gke \
  --region us-central1 \
  --project YOUR_PROJECT_ID
```

## ⚙️ Configuration

### Key Variables

```hcl
# Project
project_id = "your-gcp-project-id"  # Required
environment = "staging"  # or "production"

# Cluster
regional_cluster = false  # true for production
node_machine_type = "e2-standard-2"
node_count = 2
use_preemptible_nodes = true  # false for production
```

### Storage Classes

- **pd-balanced** (default): Cost-optimized, 3000 IOPS
- **pd-ssd-performance**: High-performance SSD
- **pd-standard-economy**: Budget option
- **pd-regional-balanced**: Multi-zone replication

## ✅ Validation

```bash
# Check cluster
kubectl get nodes
kubectl cluster-info

# Check system pods
kubectl get pods -n kube-system

# Test storage
kubectl get storageclass
```

## 💰 Cost Estimation

### Staging (~$140/month)
```
GKE Management (Zonal)    $73
Compute (2 preemptible)   $35
Persistent Disk (60GB)    $6
Cloud NAT                 $32
Data Processing           $3
Total                     ~$140/month
```

### Production (~$290/month)
```
GKE Management (Free)     $0
Compute (3 standard)      $293
Persistent Disk (150GB)   $15
Cloud NAT                 $32
Data Processing           $10
Logging & Monitoring      $8
Total                     ~$290/month
```

### Cost Optimization

1. **Committed Use Discounts**: 57% off compute (1-3 year)
2. **Preemptible Nodes**: 65% savings (staging)
3. **Right-sizing**: Monitor and adjust instance types
4. **Autoscaling**: Scale down during low usage
5. **pd-balanced**: 41% cheaper than pd-ssd

```bash
# Run cost calculator
./cost-calculator.sh
```

## 🔐 Security

- **Workload Identity**: Pod-level IAM roles
- **Private Nodes**: No external IPs
- **Shielded Nodes**: Secure boot + integrity monitoring
- **Network Policy**: Pod-to-pod traffic control
- **Encrypted Disks**: All persistent disks encrypted

## 🐛 Troubleshooting

### Issue: gcloud not authenticated
```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### Issue: APIs not enabled
```bash
gcloud services enable compute.googleapis.com
gcloud services enable container.googleapis.com
```

### Issue: kubectl can't connect
```bash
gcloud container clusters get-credentials \
  CLUSTER_NAME --region REGION --project PROJECT_ID
```

### Issue: Node group fails
```bash
# Check quotas
gcloud compute project-info describe --project=PROJECT_ID
```

## 📚 Additional Resources

- [GKE Documentation](https://cloud.google.com/kubernetes-engine/docs)
- [GCP Pricing Calculator](https://cloud.google.com/products/calculator)
- [Terraform GCP Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)

## 🔄 Maintenance

```bash
# Update cluster version
terraform apply -var="kubernetes_version=1.29"

# Scale nodes
terraform apply -var="node_count=4"

# Destroy infrastructure
terraform destroy
```

---

**Created**: 2025-10-29
**Sprint**: 3 - Infrastructure Provisioning
**Status**: Production Ready
