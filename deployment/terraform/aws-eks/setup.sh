#!/bin/bash
##
## Quick Setup Script for AWS EKS Infrastructure
##
## Usage:
##   ./setup.sh staging   # Deploy to staging
##   ./setup.sh production # Deploy to production
##

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print functions
info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if environment argument is provided
if [ $# -eq 0 ]; then
    error "Environment argument required"
    echo "Usage: $0 [staging|production]"
    exit 1
fi

ENVIRONMENT=$1

# Validate environment
if [[ "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
    error "Invalid environment: $ENVIRONMENT"
    echo "Must be either 'staging' or 'production'"
    exit 1
fi

info "🚀 Starting AWS EKS deployment for: $ENVIRONMENT"
echo ""

# Check prerequisites
info "📋 Checking prerequisites..."

command -v terraform >/dev/null 2>&1 || { error "terraform is required but not installed. Aborting."; exit 1; }
command -v aws >/dev/null 2>&1 || { error "aws cli is required but not installed. Aborting."; exit 1; }
command -v kubectl >/dev/null 2>&1 || { error "kubectl is required but not installed. Aborting."; exit 1; }

info "✅ All prerequisites installed"
echo ""

# Check AWS credentials
info "🔐 Checking AWS credentials..."
if ! aws sts get-caller-identity &> /dev/null; then
    error "AWS credentials not configured"
    echo "Run: aws configure"
    exit 1
fi

AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region)
info "✅ AWS Account: $AWS_ACCOUNT"
info "✅ AWS Region: $AWS_REGION"
echo ""

# Copy environment configuration
info "📝 Copying environment configuration..."
cp "environments/$ENVIRONMENT/terraform.tfvars" .
info "✅ Using $ENVIRONMENT configuration"
echo ""

# Initialize Terraform
info "🔧 Initializing Terraform..."
terraform init
echo ""

# Validate configuration
info "✔️  Validating configuration..."
terraform validate
echo ""

# Plan deployment
info "📊 Creating deployment plan..."
terraform plan -out="${ENVIRONMENT}.tfplan"
echo ""

# Ask for confirmation
if [ "$ENVIRONMENT" == "production" ]; then
    warn "⚠️  You are about to deploy to PRODUCTION!"
    warn "This will create real infrastructure and incur costs (~$370/month)"
    echo ""
    read -p "Are you sure you want to proceed? (type 'yes' to confirm): " confirm
    if [ "$confirm" != "yes" ]; then
        error "Deployment cancelled"
        exit 0
    fi
else
    info "ℹ️  Deploying to staging (estimated cost: ~$210/month)"
    read -p "Proceed with deployment? (y/n): " confirm
    if [ "$confirm" != "y" ]; then
        error "Deployment cancelled"
        exit 0
    fi
fi

echo ""

# Apply configuration
info "🚀 Deploying infrastructure..."
info "⏱️  This will take approximately 15-20 minutes..."
echo ""

terraform apply "${ENVIRONMENT}.tfplan"

# Get outputs
CLUSTER_NAME=$(terraform output -raw cluster_name)
CLUSTER_ENDPOINT=$(terraform output -raw cluster_endpoint)
KUBECTL_CONFIG_CMD=$(terraform output -raw configure_kubectl)

echo ""
info "✅ Infrastructure deployment complete!"
echo ""
info "📝 Cluster Details:"
info "   Name: $CLUSTER_NAME"
info "   Endpoint: ${CLUSTER_ENDPOINT:0:50}..."
echo ""

# Configure kubectl
info "🔧 Configuring kubectl..."
eval "$KUBECTL_CONFIG_CMD"
echo ""

# Verify cluster
info "✔️  Verifying cluster..."
kubectl get nodes
echo ""

# Check system pods
info "🔍 Checking system pods..."
kubectl get pods -n kube-system
echo ""

# Show storage classes
info "💾 Available storage classes:"
kubectl get storageclass
echo ""

# Show next steps
echo ""
info "🎉 Setup complete!"
echo ""
info "Next steps:"
info "1. Deploy application: cd ../../kubernetes && kubectl apply -f ."
info "2. Configure secrets: kubectl create secret generic trader-secrets --from-env-file=.env"
info "3. Check status: kubectl get pods"
echo ""

if [ "$ENVIRONMENT" == "staging" ]; then
    info "💰 Estimated monthly cost: ~$210"
else
    info "💰 Estimated monthly cost: ~$370"
fi

echo ""
info "📚 Documentation: deployment/terraform/aws-eks/README.md"
info "🔄 To destroy: terraform destroy"
echo ""

# Save cluster info
cat > cluster-info.txt <<EOF
Cluster Name: $CLUSTER_NAME
Environment: $ENVIRONMENT
AWS Region: $AWS_REGION
AWS Account: $AWS_ACCOUNT
Deployed: $(date)
Endpoint: $CLUSTER_ENDPOINT

kubectl Configuration:
$KUBECTL_CONFIG_CMD

Terraform State:
$(terraform state list | wc -l) resources created
EOF

info "ℹ️  Cluster information saved to: cluster-info.txt"
echo ""
