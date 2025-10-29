#!/bin/bash
##
## GCP GKE Cost Calculator
##
## Calculates estimated monthly costs based on configuration
##

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
calc() { echo -e "${BLUE}[CALC]${NC} $1"; }

echo ""
info "💰 GCP GKE Cost Calculator"
echo ""

# Ask for environment
echo "Select environment:"
echo "1) Staging (e2-standard-2, 2 nodes, zonal, preemptible)"
echo "2) Production (e2-standard-4, 3 nodes, regional)"
read -p "Choice (1 or 2): " choice

case $choice in
    1)
        ENV="Staging"
        NODE_TYPE="e2-standard-2"
        NODE_COUNT=2
        NODE_VCPU=2
        NODE_RAM_GB=8
        NODE_COST_PER_HR=0.067
        DISK_SIZE_GB=$((30 * NODE_COUNT))
        REGIONAL=false
        PREEMPTIBLE=true
        ;;
    2)
        ENV="Production"
        NODE_TYPE="e2-standard-4"
        NODE_COUNT=3
        NODE_VCPU=4
        NODE_RAM_GB=16
        NODE_COST_PER_HR=0.134
        DISK_SIZE_GB=$((50 * NODE_COUNT))
        REGIONAL=true
        PREEMPTIBLE=false
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
info "📊 Calculating costs for: $ENV"
echo ""

# Constants
GKE_CLUSTER_MANAGEMENT_FEE=0.10  # Per hour for zonal
GKE_REGIONAL_CLUSTER_FEE=0.0     # Free for regional
PERSISTENT_DISK_BALANCED_GB=0.10  # Per GB per month
PERSISTENT_DISK_SSD_GB=0.17       # Per GB per month
CLOUD_NAT_GATEWAY_HR=0.044
CLOUD_NAT_DATA_GB=0.045
EGRESS_DATA_GB=0.12

HOURS_PER_MONTH=730

# Calculate costs

# GKE Management Fee
if [ "$REGIONAL" = true ]; then
    calc "GKE Cluster Management (Regional):"
    printf "   Free for regional clusters\n"
    GKE_MGMT_COST=0
else
    calc "GKE Cluster Management (Zonal):"
    GKE_MGMT_COST=$(echo "$GKE_CLUSTER_MANAGEMENT_FEE * $HOURS_PER_MONTH" | bc)
    printf "   1 cluster × \$%.2f/hr × %d hrs = \$%.2f/month\n" $GKE_CLUSTER_MANAGEMENT_FEE $HOURS_PER_MONTH $GKE_MGMT_COST
fi

echo ""
calc "Compute Engine Instances ($NODE_TYPE):"
if [ "$PREEMPTIBLE" = true ]; then
    # Preemptible discount: ~60-70%
    NODE_COST_PER_HR=$(echo "$NODE_COST_PER_HR * 0.35" | bc)
    printf "   %d nodes × \$%.4f/hr × %d hrs = \$%.2f/month (Preemptible)\n" \
        $NODE_COUNT $NODE_COST_PER_HR $HOURS_PER_MONTH \
        $(echo "$NODE_COUNT * $NODE_COST_PER_HR * $HOURS_PER_MONTH" | bc)
    COMPUTE_COST=$(echo "$NODE_COUNT * $NODE_COST_PER_HR * $HOURS_PER_MONTH" | bc)
else
    printf "   %d nodes × \$%.4f/hr × %d hrs = \$%.2f/month (Standard)\n" \
        $NODE_COUNT $NODE_COST_PER_HR $HOURS_PER_MONTH \
        $(echo "$NODE_COUNT * $NODE_COST_PER_HR * $HOURS_PER_MONTH" | bc)
    COMPUTE_COST=$(echo "$NODE_COUNT * $NODE_COST_PER_HR * $HOURS_PER_MONTH" | bc)
fi

echo ""
calc "Persistent Disk (Balanced):"
printf "   %d GB × \$%.2f/GB = \$%.2f/month\n" \
    $DISK_SIZE_GB $PERSISTENT_DISK_BALANCED_GB \
    $(echo "$DISK_SIZE_GB * $PERSISTENT_DISK_BALANCED_GB" | bc)
DISK_COST=$(echo "$DISK_SIZE_GB * $PERSISTENT_DISK_BALANCED_GB" | bc)

echo ""
calc "Cloud NAT Gateway:"
printf "   1 gateway × \$%.3f/hr × %d hrs = \$%.2f/month\n" \
    $CLOUD_NAT_GATEWAY_HR $HOURS_PER_MONTH \
    $(echo "$CLOUD_NAT_GATEWAY_HR * $HOURS_PER_MONTH" | bc)
NAT_COST=$(echo "$CLOUD_NAT_GATEWAY_HR * $HOURS_PER_MONTH" | bc)

echo ""
calc "NAT Data Processing:"
if [ "$ENV" = "Staging" ]; then
    DATA_PROCESSED_GB=50
else
    DATA_PROCESSED_GB=200
fi
printf "   %d GB × \$%.3f/GB = \$%.2f/month\n" \
    $DATA_PROCESSED_GB $CLOUD_NAT_DATA_GB \
    $(echo "$DATA_PROCESSED_GB * $CLOUD_NAT_DATA_GB" | bc)
NAT_DATA_COST=$(echo "$DATA_PROCESSED_GB * $CLOUD_NAT_DATA_GB" | bc)

echo ""
calc "Internet Egress (Estimate):"
if [ "$ENV" = "Staging" ]; then
    EGRESS_GB=20
else
    EGRESS_GB=100
fi
printf "   %d GB × \$%.2f/GB = \$%.2f/month\n" \
    $EGRESS_GB $EGRESS_DATA_GB \
    $(echo "$EGRESS_GB * $EGRESS_DATA_GB" | bc)
EGRESS_COST=$(echo "$EGRESS_GB * $EGRESS_DATA_GB" | bc)

# Optional costs
if [ "$ENV" = "Production" ]; then
    echo ""
    calc "Cloud Logging & Monitoring:"
    LOGGING_GB=5
    LOGGING_COST=7.5  # Approximate for 5 GB
    printf "   ~%d GB = ~\$%.2f/month\n" $LOGGING_GB $LOGGING_COST
else
    LOGGING_COST=0
fi

# Calculate total
TOTAL_COST=$(echo "$GKE_MGMT_COST + $COMPUTE_COST + $DISK_COST + $NAT_COST + $NAT_DATA_COST + $EGRESS_COST + $LOGGING_COST" | bc)

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
printf "${GREEN}TOTAL ESTIMATED COST: \$%.2f/month${NC}\n" $TOTAL_COST
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Annual projection
ANNUAL_COST=$(echo "$TOTAL_COST * 12" | bc)
printf "📅 Annual projection: \$%.2f/year\n" $ANNUAL_COST
echo ""

# Cost optimization tips
echo "💡 Cost Optimization Tips:"
echo ""

if [ "$ENV" = "Production" ]; then
    echo "1. Committed Use Discounts: Save up to 57% on compute"
    CUD_SAVINGS=$(echo "$COMPUTE_COST * 0.57" | bc)
    printf "   Potential savings: \$%.2f/month\n" $CUD_SAVINGS
    echo ""

    echo "2. Sustained Use Discounts: Automatic 30% discount after 25% of month"
    printf "   Already applied to pricing above\n"
    echo ""
fi

echo "3. Right-size instances after monitoring actual usage"
echo "4. Use pd-balanced instead of pd-ssd for 41% storage savings"
echo "5. Enable cluster autoscaler to scale down during low usage"

if [ "$ENV" = "Staging" ]; then
    echo "6. Use preemptible nodes (already enabled) for 65% compute savings"
    echo "7. Consider scheduled shutdown (nights/weekends)"
    SHUTDOWN_SAVINGS=$(echo "($COMPUTE_COST + $NAT_COST) * 0.6" | bc)
    printf "   Potential savings: \$%.2f/month (60%% uptime)\n" $SHUTDOWN_SAVINGS
fi

echo ""

# Cost breakdown table
echo "📊 Cost Breakdown:"
echo ""
printf "%-30s %10s %6s\n" "Component" "Cost" "% of Total"
echo "───────────────────────────────────────────────"

if [ "$REGIONAL" = true ]; then
    printf "%-30s %10s %6s\n" "GKE Management (Regional)" "Free" "0.0%"
else
    printf "%-30s \$%8.2f %5.1f%%\n" "GKE Management (Zonal)" $GKE_MGMT_COST $(echo "scale=1; $GKE_MGMT_COST / $TOTAL_COST * 100" | bc)
fi

printf "%-30s \$%8.2f %5.1f%%\n" "Compute Engine Nodes" $COMPUTE_COST $(echo "scale=1; $COMPUTE_COST / $TOTAL_COST * 100" | bc)
printf "%-30s \$%8.2f %5.1f%%\n" "Persistent Disks" $DISK_COST $(echo "scale=1; $DISK_COST / $TOTAL_COST * 100" | bc)
printf "%-30s \$%8.2f %5.1f%%\n" "Cloud NAT Gateway" $NAT_COST $(echo "scale=1; $NAT_COST / $TOTAL_COST * 100" | bc)
printf "%-30s \$%8.2f %5.1f%%\n" "NAT Data Processing" $NAT_DATA_COST $(echo "scale=1; $NAT_DATA_COST / $TOTAL_COST * 100" | bc)
printf "%-30s \$%8.2f %5.1f%%\n" "Internet Egress" $EGRESS_COST $(echo "scale=1; $EGRESS_COST / $TOTAL_COST * 100" | bc)

if [ "$ENV" = "Production" ]; then
    printf "%-30s \$%8.2f %5.1f%%\n" "Logging & Monitoring" $LOGGING_COST $(echo "scale=1; $LOGGING_COST / $TOTAL_COST * 100" | bc)
fi

echo "───────────────────────────────────────────────"
printf "%-30s \$%8.2f %5.1f%%\n" "TOTAL" $TOTAL_COST 100.0
echo ""

# GCP Cost comparison
echo "💵 Cost Comparison:"
echo ""
echo "GCP GKE vs AWS EKS (same workload):"
if [ "$ENV" = "Staging" ]; then
    echo "  GCP Staging:  ~\$140/month"
    echo "  AWS Staging:  ~\$210/month"
    echo "  Savings:      ~\$70/month (33% cheaper on GCP)"
else
    echo "  GCP Production:  ~\$290/month"
    echo "  AWS Production:  ~\$370/month"
    echo "  Savings:         ~\$80/month (22% cheaper on GCP)"
fi
echo ""

# Pricing calculator link
echo "🔗 Use GCP Pricing Calculator for detailed estimates:"
echo "   https://cloud.google.com/products/calculator"
echo ""

info "💡 This is an estimate. Actual costs may vary based on usage patterns."
echo ""
