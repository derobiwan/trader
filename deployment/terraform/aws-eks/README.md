# AWS EKS Infrastructure Terraform Configuration

Infrastructure-as-Code for deploying the LLM Crypto Trading System on AWS EKS (Elastic Kubernetes Service).

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Architecture Overview](#architecture-overview)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Validation](#validation)
- [Cost Estimation](#cost-estimation)
- [Maintenance](#maintenance)
- [Troubleshooting](#troubleshooting)

## 🔧 Prerequisites

### Required Tools

```bash
# Install Terraform (>= 1.6.0)
brew install terraform  # macOS
# or
wget https://releases.hashicorp.com/terraform/1.6.6/terraform_1.6.6_linux_amd64.zip
unzip terraform_1.6.6_linux_amd64.zip
sudo mv terraform /usr/local/bin/

# Install AWS CLI (>= 2.13.0)
brew install awscli  # macOS
# or
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Install kubectl (>= 1.28)
brew install kubectl  # macOS
# or
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Verify installations
terraform --version
aws --version
kubectl version --client
```

### AWS Account Setup

1. **AWS Account**: Active AWS account with billing enabled
2. **IAM User**: Create IAM user with required permissions:
   - AmazonEC2FullAccess
   - AmazonEKSClusterPolicy
   - AmazonEKSServicePolicy
   - AmazonVPCFullAccess
   - IAMFullAccess
   - AmazonS3FullAccess (for Terraform state)

3. **Configure AWS CLI**:
```bash
aws configure
# Enter:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region (us-east-1)
# - Default output format (json)

# Verify
aws sts get-caller-identity
```

## 🏗️ Architecture Overview

### Infrastructure Components

```
┌─────────────────────────────────────────────────────────────┐
│                         AWS Region                           │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                        VPC                             │  │
│  │  ┌──────────────┐           ┌──────────────┐         │  │
│  │  │  AZ 1        │           │  AZ 2        │         │  │
│  │  │              │           │              │         │  │
│  │  │  Public      │           │  Public      │         │  │
│  │  │  Subnet      │           │  Subnet      │         │  │
│  │  │  10.0.1.0/24 │           │  10.0.2.0/24 │         │  │
│  │  │  ┌──────┐    │           │  ┌──────┐    │         │  │
│  │  │  │ NAT  │    │           │  │ NAT  │    │         │  │
│  │  │  │  GW  │    │           │  │  GW  │    │         │  │
│  │  │  └──────┘    │           │  └──────┘    │         │  │
│  │  │              │           │              │         │  │
│  │  │  Private     │           │  Private     │         │  │
│  │  │  Subnet      │           │  Subnet      │         │  │
│  │  │  10.0.10/24  │           │  10.0.20/24  │         │  │
│  │  │  ┌────────┐  │           │  ┌────────┐  │         │  │
│  │  │  │ EKS    │  │           │  │ EKS    │  │         │  │
│  │  │  │ Node 1 │  │           │  │ Node 2 │  │         │  │
│  │  │  │ Node 3 │  │           │  │        │  │         │  │
│  │  │  └────────┘  │           │  └────────┘  │         │  │
│  │  └──────────────┘           └──────────────┘         │  │
│  │                                                        │  │
│  │  ┌──────────────────────────────────────────────┐    │  │
│  │  │         EKS Control Plane                     │    │  │
│  │  │  (Managed by AWS)                             │    │  │
│  │  └──────────────────────────────────────────────┘    │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Resource Breakdown

| Component | Resource | Configuration |
|-----------|----------|---------------|
| **VPC** | VPC | 10.0.0.0/16 (staging) / 10.1.0.0/16 (prod) |
| | Public Subnets | 2 subnets across 2 AZs |
| | Private Subnets | 2 subnets across 2 AZs |
| | NAT Gateways | 2 (one per AZ) |
| | Internet Gateway | 1 |
| **EKS** | Control Plane | Managed by AWS |
| | Worker Nodes | 3 nodes (t3.large) |
| | Node Disk | 50GB EBS gp3 per node |
| **Storage** | EBS CSI Driver | Enabled |
| | Storage Classes | gp3, io1, gp2 |
| **Monitoring** | CloudWatch Logs | Control plane logs |

## 🚀 Quick Start

### 1. Clone and Navigate

```bash
cd deployment/terraform/aws-eks
```

### 2. Choose Environment

```bash
# For staging
cp environments/staging/terraform.tfvars .

# For production
cp environments/production/terraform.tfvars .
```

### 3. Review and Customize

Edit `terraform.tfvars` as needed:

```hcl
# Critical variables to review:
project_name = "llm-crypto-trader"
environment  = "staging"  # or "production"
owner        = "your-email@example.com"
aws_region   = "us-east-1"

# Node configuration
node_instance_types = ["t3.large"]
node_desired_size   = 3
```

### 4. Initialize Terraform

```bash
terraform init
```

### 5. Plan Deployment

```bash
terraform plan -out=tfplan
```

Review the plan carefully. You should see approximately:
- **Staging**: ~35 resources to be created
- **Production**: ~40 resources to be created

### 6. Apply Configuration

```bash
terraform apply tfplan
```

Deployment time: **15-20 minutes**

### 7. Configure kubectl

```bash
aws eks update-kubeconfig \
  --region us-east-1 \
  --name llm-crypto-trader-staging-eks

# Verify
kubectl get nodes
```

Expected output:
```
NAME                         STATUS   ROLES    AGE   VERSION
ip-10-0-10-123.ec2.internal  Ready    <none>   5m    v1.28.x
ip-10-0-10-456.ec2.internal  Ready    <none>   5m    v1.28.x
ip-10-0-20-789.ec2.internal  Ready    <none>   5m    v1.28.x
```

## ⚙️ Configuration

### Environment Variables

```bash
# Set environment
export TF_VAR_environment="staging"

# Set AWS profile if using multiple profiles
export AWS_PROFILE="trader-dev"

# Set region
export AWS_DEFAULT_REGION="us-east-1"
```

### Terraform Backend (Recommended for Team)

Configure S3 backend for shared state:

1. Create S3 bucket and DynamoDB table:

```bash
# Create S3 bucket for state
aws s3 mb s3://trader-terraform-state --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket trader-terraform-state \
  --versioning-configuration Status=Enabled

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name trader-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

2. Uncomment backend configuration in `main.tf`:

```hcl
backend "s3" {
  bucket         = "trader-terraform-state"
  key            = "eks/terraform.tfstate"
  region         = "us-east-1"
  encrypt        = true
  dynamodb_table = "trader-terraform-locks"
}
```

3. Re-initialize:

```bash
terraform init -migrate-state
```

## 📦 Deployment

### Staging Deployment

```bash
# Use staging configuration
cp environments/staging/terraform.tfvars .

# Initialize
terraform init

# Plan
terraform plan -out=staging.tfplan

# Apply
terraform apply staging.tfplan

# Configure kubectl
aws eks update-kubeconfig \
  --region us-east-1 \
  --name llm-crypto-trader-staging-eks
```

### Production Deployment

```bash
# Use production configuration
cp environments/production/terraform.tfvars .

# Initialize
terraform init

# Plan and save
terraform plan -out=production.tfplan

# Review plan carefully!
# Verify node count, instance types, costs

# Apply
terraform apply production.tfplan

# Configure kubectl
aws eks update-kubeconfig \
  --region us-east-1 \
  --name llm-crypto-trader-production-eks
```

### Multi-Environment Management

Use workspaces:

```bash
# Create workspaces
terraform workspace new staging
terraform workspace new production

# Switch to staging
terraform workspace select staging
terraform apply -var-file=environments/staging/terraform.tfvars

# Switch to production
terraform workspace select production
terraform apply -var-file=environments/production/terraform.tfvars

# List workspaces
terraform workspace list
```

## ✅ Validation

### Infrastructure Validation

```bash
# Verify Terraform state
terraform show
terraform output

# Verify AWS resources
aws eks describe-cluster --name llm-crypto-trader-staging-eks
aws eks list-nodegroups --cluster-name llm-crypto-trader-staging-eks
```

### Kubernetes Validation

```bash
# Check cluster info
kubectl cluster-info

# Check nodes
kubectl get nodes -o wide

# Check system pods
kubectl get pods -n kube-system

# Check storage classes
kubectl get storageclass

# Test storage provisioning
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: test-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
  storageClassName: gp3
EOF

kubectl get pvc test-pvc
kubectl delete pvc test-pvc
```

### Network Validation

```bash
# Test DNS resolution
kubectl run -it --rm debug --image=busybox --restart=Never -- nslookup kubernetes.default

# Test internet connectivity
kubectl run -it --rm debug --image=busybox --restart=Never -- wget -O- https://google.com
```

## 💰 Cost Estimation

### Staging Environment

| Resource | Quantity | Unit Cost | Monthly Cost |
|----------|----------|-----------|--------------|
| EKS Control Plane | 1 | $0.10/hr | $73 |
| EC2 t3.medium | 2 | $0.0416/hr | $61 |
| EBS gp3 (30GB x 2) | 60GB | $0.08/GB | $5 |
| NAT Gateway | 2 | $0.045/hr | $66 |
| NAT Data Transfer | 100GB | $0.045/GB | $5 |
| **Total Staging** | | | **~$210/mo** |

### Production Environment

| Resource | Quantity | Unit Cost | Monthly Cost |
|----------|----------|-----------|--------------|
| EKS Control Plane | 1 | $0.10/hr | $73 |
| EC2 t3.large | 3 | $0.0832/hr | $183 |
| EBS gp3 (50GB x 3) | 150GB | $0.08/GB | $12 |
| NAT Gateway | 2 | $0.045/hr | $66 |
| NAT Data Transfer | 500GB | $0.045/GB | $23 |
| EBS Snapshots | 150GB | $0.05/GB | $8 |
| CloudWatch Logs | 10GB | $0.50/GB | $5 |
| **Total Production** | | | **~$370/mo** |

### Cost Optimization Tips

1. **Use Spot Instances in Staging**: ~70% cost reduction
2. **Right-size Nodes**: Monitor and adjust instance types
3. **Enable Cluster Autoscaler**: Scale down during low usage
4. **Use EBS gp3**: 20% cheaper than gp2
5. **Optimize NAT**: Use single NAT gateway in staging
6. **Reserved Instances**: 40-60% savings for production
7. **Savings Plans**: Flexible commitment savings

## 🔄 Maintenance

### Updates

```bash
# Update Terraform providers
terraform init -upgrade

# Update cluster version
# 1. Update cluster_version in terraform.tfvars
# 2. Apply
terraform plan
terraform apply

# Update node AMI
# Terraform will automatically use latest EKS-optimized AMI
# Or force update:
terraform apply -replace=module.eks.aws_eks_node_group.main["general"]
```

### Backup

```bash
# Backup Terraform state
terraform state pull > terraform.tfstate.backup

# Backup kubectl config
kubectl config view --raw > kubeconfig.backup

# Snapshot EBS volumes (automated if enabled)
aws ec2 describe-snapshots \
  --owner-ids self \
  --filters "Name=tag:cluster-name,Values=llm-crypto-trader-*"
```

### Monitoring

```bash
# View CloudWatch logs
aws logs tail /aws/eks/llm-crypto-trader-staging-eks/cluster --follow

# Cluster metrics
kubectl top nodes
kubectl top pods --all-namespaces

# Cost tracking
aws ce get-cost-and-usage \
  --time-period Start=2025-10-01,End=2025-10-31 \
  --granularity MONTHLY \
  --metrics UnblendedCost \
  --filter file://cost-filter.json
```

## 🐛 Troubleshooting

### Common Issues

#### Issue: Terraform init fails

```bash
# Clear cache and retry
rm -rf .terraform .terraform.lock.hcl
terraform init
```

#### Issue: Node group fails to create

```bash
# Check IAM permissions
aws iam get-role --role-name llm-crypto-trader-staging-eks-node-group-role

# Check subnet tags (required by EKS)
aws ec2 describe-subnets --subnet-ids <subnet-id>
```

#### Issue: kubectl can't connect

```bash
# Reconfigure kubectl
aws eks update-kubeconfig \
  --region us-east-1 \
  --name llm-crypto-trader-staging-eks

# Verify AWS credentials
aws sts get-caller-identity

# Check cluster status
aws eks describe-cluster --name llm-crypto-trader-staging-eks
```

#### Issue: Pods can't pull images

```bash
# Verify node IAM role has ECR permissions
aws iam list-attached-role-policies \
  --role-name llm-crypto-trader-staging-eks-node-group-role

# Should include: AmazonEC2ContainerRegistryReadOnly
```

#### Issue: Storage provisioning fails

```bash
# Check EBS CSI driver
kubectl get pods -n kube-system | grep ebs-csi

# Verify IAM policy
aws iam list-attached-role-policies \
  --role-name llm-crypto-trader-staging-eks-node-group-role | grep EBS
```

### Logs and Debugging

```bash
# Terraform debug logs
export TF_LOG=DEBUG
terraform apply

# kubectl verbose output
kubectl get pods -v=8

# Node logs
kubectl logs -n kube-system <pod-name>
```

## 🚀 Next Steps

After infrastructure is provisioned:

1. **Deploy Application**:
   ```bash
   cd ../../kubernetes
   kubectl apply -f configmap.yaml
   kubectl apply -f secrets.yaml
   kubectl apply -f deployment.yaml
   ```

2. **Configure Monitoring**:
   ```bash
   kubectl apply -f monitoring/
   ```

3. **Set up CI/CD**:
   - Configure GitHub Actions secrets
   - Test deployment pipeline

4. **Validate System**:
   - Run health checks
   - Execute smoke tests
   - Monitor performance

## 📚 Additional Resources

- [AWS EKS Best Practices](https://aws.github.io/aws-eks-best-practices/)
- [Terraform AWS EKS Module](https://registry.terraform.io/modules/terraform-aws-modules/eks/aws/latest)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [AWS EKS Pricing](https://aws.amazon.com/eks/pricing/)

## 🔐 Security Considerations

1. **IAM Roles**: Use least-privilege principle
2. **Network Policies**: Implement Kubernetes network policies
3. **Secrets Management**: Use AWS Secrets Manager or HashiCorp Vault
4. **Pod Security**: Enable Pod Security Standards
5. **Image Scanning**: Scan container images before deployment
6. **Audit Logging**: Enable and monitor CloudWatch logs

## 📧 Support

For issues or questions:
- Open an issue in the repository
- Check troubleshooting section above
- Review AWS EKS documentation

---

**Created**: 2025-10-29
**Sprint**: 3 - Infrastructure Provisioning
**Status**: Production Ready
