#!/bin/bash
##
## AWS EKS Cost Calculator
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
info "💰 AWS EKS Cost Calculator"
echo ""

# Ask for environment
echo "Select environment:"
echo "1) Staging (t3.medium, 2 nodes)"
echo "2) Production (t3.large, 3 nodes)"
read -p "Choice (1 or 2): " choice

case $choice in
    1)
        ENV="Staging"
        NODE_TYPE="t3.medium"
        NODE_COUNT=2
        NODE_COST_PER_HR=0.0416
        DISK_SIZE_GB=$((30 * NODE_COUNT))
        DATA_TRANSFER_GB=100
        SPOT_ENABLED=true
        ;;
    2)
        ENV="Production"
        NODE_TYPE="t3.large"
        NODE_COUNT=3
        NODE_COST_PER_HR=0.0832
        DISK_SIZE_GB=$((50 * NODE_COUNT))
        DATA_TRANSFER_GB=500
        SPOT_ENABLED=false
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
EKS_CONTROL_PLANE_HR=0.10
NAT_GATEWAY_HR=0.045
EBS_GP3_GB_MONTH=0.08
NAT_DATA_GB=0.045
SNAPSHOT_GB_MONTH=0.05
CLOUDWATCH_GB_MONTH=0.50

HOURS_PER_MONTH=730

# Calculate costs
calc "EKS Control Plane:"
EKS_CONTROL_COST=$(echo "$EKS_CONTROL_PLANE_HR * $HOURS_PER_MONTH" | bc)
printf "   1 cluster × \$%.2f/hr × %d hrs = \$%.2f/month\n" $EKS_CONTROL_PLANE_HR $HOURS_PER_MONTH $EKS_CONTROL_COST

echo ""
calc "EC2 Instances ($NODE_TYPE):"
if [ "$SPOT_ENABLED" = true ]; then
    NODE_COST_PER_HR=$(echo "$NODE_COST_PER_HR * 0.3" | bc)  # 70% discount for spot
    printf "   %d nodes × \$%.4f/hr × %d hrs = \$%.2f/month (Spot)\n" \
        $NODE_COUNT $NODE_COST_PER_HR $HOURS_PER_MONTH \
        $(echo "$NODE_COUNT * $NODE_COST_PER_HR * $HOURS_PER_MONTH" | bc)
    EC2_COST=$(echo "$NODE_COUNT * $NODE_COST_PER_HR * $HOURS_PER_MONTH" | bc)
else
    printf "   %d nodes × \$%.4f/hr × %d hrs = \$%.2f/month (On-Demand)\n" \
        $NODE_COUNT $NODE_COST_PER_HR $HOURS_PER_MONTH \
        $(echo "$NODE_COUNT * $NODE_COST_PER_HR * $HOURS_PER_MONTH" | bc)
    EC2_COST=$(echo "$NODE_COUNT * $NODE_COST_PER_HR * $HOURS_PER_MONTH" | bc)
fi

echo ""
calc "EBS Storage (gp3):"
printf "   %d GB × \$%.2f/GB = \$%.2f/month\n" \
    $DISK_SIZE_GB $EBS_GP3_GB_MONTH \
    $(echo "$DISK_SIZE_GB * $EBS_GP3_GB_MONTH" | bc)
EBS_COST=$(echo "$DISK_SIZE_GB * $EBS_GP3_GB_MONTH" | bc)

echo ""
calc "NAT Gateways:"
printf "   2 gateways × \$%.3f/hr × %d hrs = \$%.2f/month\n" \
    $NAT_GATEWAY_HR $HOURS_PER_MONTH \
    $(echo "2 * $NAT_GATEWAY_HR * $HOURS_PER_MONTH" | bc)
NAT_COST=$(echo "2 * $NAT_GATEWAY_HR * $HOURS_PER_MONTH" | bc)

echo ""
calc "NAT Data Transfer:"
printf "   %d GB × \$%.3f/GB = \$%.2f/month\n" \
    $DATA_TRANSFER_GB $NAT_DATA_GB \
    $(echo "$DATA_TRANSFER_GB * $NAT_DATA_GB" | bc)
NAT_DATA_COST=$(echo "$DATA_TRANSFER_GB * $NAT_DATA_GB" | bc)

# Optional costs
if [ "$ENV" = "Production" ]; then
    echo ""
    calc "EBS Snapshots:"
    printf "   %d GB × \$%.2f/GB = \$%.2f/month\n" \
        $DISK_SIZE_GB $SNAPSHOT_GB_MONTH \
        $(echo "$DISK_SIZE_GB * $SNAPSHOT_GB_MONTH" | bc)
    SNAPSHOT_COST=$(echo "$DISK_SIZE_GB * $SNAPSHOT_GB_MONTH" | bc)

    echo ""
    calc "CloudWatch Logs:"
    CLOUDWATCH_GB=10
    printf "   %d GB × \$%.2f/GB = \$%.2f/month\n" \
        $CLOUDWATCH_GB $CLOUDWATCH_GB_MONTH \
        $(echo "$CLOUDWATCH_GB * $CLOUDWATCH_GB_MONTH" | bc)
    CLOUDWATCH_COST=$(echo "$CLOUDWATCH_GB * $CLOUDWATCH_GB_MONTH" | bc)
else
    SNAPSHOT_COST=0
    CLOUDWATCH_COST=0
fi

# Calculate total
TOTAL_COST=$(echo "$EKS_CONTROL_COST + $EC2_COST + $EBS_COST + $NAT_COST + $NAT_DATA_COST + $SNAPSHOT_COST + $CLOUDWATCH_COST" | bc)

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
    echo "1. Reserved Instances: Save 40-60% on EC2 costs"
    RI_SAVINGS=$(echo "$EC2_COST * 0.5" | bc)
    printf "   Potential savings: \$%.2f/month\n" $RI_SAVINGS
    echo ""

    echo "2. Compute Savings Plans: Flexible 1-3 year commitment"
    printf "   Potential savings: \$%.2f/month\n" $(echo "$EC2_COST * 0.4" | bc)
    echo ""
fi

echo "3. Right-size instances after monitoring actual usage"
echo "4. Enable cluster autoscaler to scale down during low usage"
echo "5. Use gp3 instead of gp2 for 20% storage cost savings"

if [ "$ENV" = "Staging" ]; then
    echo "6. Consider scheduled shutdown (nights/weekends)"
    SHUTDOWN_SAVINGS=$(echo "($EC2_COST + $NAT_COST) * 0.6" | bc)
    printf "   Potential savings: \$%.2f/month (60%% uptime)\n" $SHUTDOWN_SAVINGS
fi

echo ""

# Cost breakdown table
echo "📊 Cost Breakdown:"
echo ""
printf "%-25s %10s %6s\n" "Component" "Cost" "% of Total"
echo "───────────────────────────────────────────"
printf "%-25s \$%8.2f %5.1f%%\n" "EKS Control Plane" $EKS_CONTROL_COST $(echo "scale=1; $EKS_CONTROL_COST / $TOTAL_COST * 100" | bc)
printf "%-25s \$%8.2f %5.1f%%\n" "EC2 Instances" $EC2_COST $(echo "scale=1; $EC2_COST / $TOTAL_COST * 100" | bc)
printf "%-25s \$%8.2f %5.1f%%\n" "EBS Storage" $EBS_COST $(echo "scale=1; $EBS_COST / $TOTAL_COST * 100" | bc)
printf "%-25s \$%8.2f %5.1f%%\n" "NAT Gateways" $NAT_COST $(echo "scale=1; $NAT_COST / $TOTAL_COST * 100" | bc)
printf "%-25s \$%8.2f %5.1f%%\n" "Data Transfer" $NAT_DATA_COST $(echo "scale=1; $NAT_DATA_COST / $TOTAL_COST * 100" | bc)

if [ "$ENV" = "Production" ]; then
    printf "%-25s \$%8.2f %5.1f%%\n" "Snapshots" $SNAPSHOT_COST $(echo "scale=1; $SNAPSHOT_COST / $TOTAL_COST * 100" | bc)
    printf "%-25s \$%8.2f %5.1f%%\n" "CloudWatch Logs" $CLOUDWATCH_COST $(echo "scale=1; $CLOUDWATCH_COST / $TOTAL_COST * 100" | bc)
fi

echo "───────────────────────────────────────────"
printf "%-25s \$%8.2f %5.1f%%\n" "TOTAL" $TOTAL_COST 100.0
echo ""

# AWS Cost Explorer command
echo "📈 Track actual costs with AWS Cost Explorer:"
echo ""
echo "aws ce get-cost-and-usage \\"
echo "  --time-period Start=$(date -u -d '1 month ago' +%Y-%m-%d),End=$(date -u +%Y-%m-%d) \\"
echo "  --granularity MONTHLY \\"
echo "  --metrics UnblendedCost \\"
echo "  --filter file://cost-filter.json"
echo ""

info "💡 This is an estimate. Actual costs may vary based on usage patterns."
echo ""
