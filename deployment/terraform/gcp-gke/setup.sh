#!/bin/bash
##
## Quick Setup Script for GCP GKE Infrastructure
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

info "🚀 Starting GCP GKE deployment for: $ENVIRONMENT"
echo ""

# Check prerequisites
info "📋 Checking prerequisites..."

command -v terraform >/dev/null 2>&1 || { error "terraform is required but not installed. Aborting."; exit 1; }
command -v gcloud >/dev/null 2>&1 || { error "gcloud CLI is required but not installed. Aborting."; exit 1; }
command -v kubectl >/dev/null 2>&1 || { error "kubectl is required but not installed. Aborting."; exit 1; }

info "✅ All prerequisites installed"
echo ""

# Check GCP authentication
info "🔐 Checking GCP authentication..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    error "GCP authentication required"
    echo "Run: gcloud auth login"
    exit 1
fi

GCP_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n 1)
GCP_PROJECT=$(gcloud config get-value project 2>/dev/null)

if [ -z "$GCP_PROJECT" ]; then
    error "No active GCP project set"
    echo "Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

info "✅ GCP Account: $GCP_ACCOUNT"
info "✅ GCP Project: $GCP_PROJECT"
echo ""

# Copy environment configuration
info "📝 Copying environment configuration..."
cp "environments/$ENVIRONMENT/terraform.tfvars" .

# Check if project ID is set
if grep -q "your-gcp-project-id" terraform.tfvars; then
    warn "⚠️  Project ID not configured in terraform.tfvars"
    info "Updating terraform.tfvars with active project: $GCP_PROJECT"
    sed -i.bak "s/your-gcp-project-id/$GCP_PROJECT/" terraform.tfvars
    rm terraform.tfvars.bak
fi

info "✅ Using $ENVIRONMENT configuration"
echo ""

# Enable required GCP APIs
info "🔧 Enabling required GCP APIs..."
REQUIRED_APIS=(
    "compute.googleapis.com"
    "container.googleapis.com"
    "cloudresourcemanager.googleapis.com"
)

for api in "${REQUIRED_APIS[@]}"; do
    info "Enabling $api..."
    gcloud services enable $api --project=$GCP_PROJECT 2>/dev/null || true
done
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
    warn "This will create real infrastructure and incur costs (~$290/month)"
    echo ""
    read -p "Are you sure you want to proceed? (type 'yes' to confirm): " confirm
    if [ "$confirm" != "yes" ]; then
        error "Deployment cancelled"
        exit 0
    fi
else
    info "ℹ️  Deploying to staging (estimated cost: ~$140/month)"
    read -p "Proceed with deployment? (y/n): " confirm
    if [ "$confirm" != "y" ]; then
        error "Deployment cancelled"
        exit 0
    fi
fi

echo ""

# Apply configuration
info "🚀 Deploying infrastructure..."
info "⏱️  This will take approximately 10-15 minutes..."
echo ""

terraform apply "${ENVIRONMENT}.tfplan"

# Get outputs
CLUSTER_NAME=$(terraform output -raw cluster_name)
CLUSTER_ENDPOINT=$(terraform output -raw cluster_endpoint)
CLUSTER_LOCATION=$(terraform output -raw cluster_location)
KUBECTL_CONFIG_CMD=$(terraform output -raw configure_kubectl)

echo ""
info "✅ Infrastructure deployment complete!"
echo ""
info "📝 Cluster Details:"
info "   Name: $CLUSTER_NAME"
info "   Location: $CLUSTER_LOCATION"
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
    info "💰 Estimated monthly cost: ~$140"
else
    info "💰 Estimated monthly cost: ~$290"
fi

echo ""
info "📚 Documentation: deployment/terraform/gcp-gke/README.md"
info "🔄 To destroy: terraform destroy"
echo ""

# Save cluster info
cat > cluster-info.txt <<EOF
Cluster Name: $CLUSTER_NAME
Environment: $ENVIRONMENT
GCP Project: $GCP_PROJECT
Region/Zone: $CLUSTER_LOCATION
Deployed: $(date)
Endpoint: $CLUSTER_ENDPOINT

kubectl Configuration:
$KUBECTL_CONFIG_CMD

Terraform State:
$(terraform state list | wc -l) resources created
EOF

info "ℹ️  Cluster information saved to: cluster-info.txt"
echo ""
