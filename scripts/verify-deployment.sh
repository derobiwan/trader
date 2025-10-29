#!/bin/bash

# Kubernetes Deployment Verification Script
# Verifies that all components are deployed correctly and healthy

set -e

NAMESPACE="trading-system"
TIMEOUT=300  # 5 minutes

echo "============================================"
echo "Kubernetes Deployment Verification"
echo "============================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
    fi
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}kubectl not found. Please install kubectl first.${NC}"
    exit 1
fi

# Check if namespace exists
echo "Checking namespace..."
if kubectl get namespace $NAMESPACE &> /dev/null; then
    print_status 0 "Namespace $NAMESPACE exists"
else
    print_status 1 "Namespace $NAMESPACE does not exist"
    echo "Please run: kubectl apply -f kubernetes/namespace.yaml"
    exit 1
fi

echo ""
echo "Checking deployments..."

# Check PostgreSQL
echo -n "PostgreSQL StatefulSet: "
if kubectl get statefulset postgres -n $NAMESPACE &> /dev/null; then
    READY=$(kubectl get statefulset postgres -n $NAMESPACE -o jsonpath='{.status.readyReplicas}')
    DESIRED=$(kubectl get statefulset postgres -n $NAMESPACE -o jsonpath='{.status.replicas}')
    if [ "$READY" == "$DESIRED" ]; then
        print_status 0 "$READY/$DESIRED replicas ready"
    else
        print_status 1 "$READY/$DESIRED replicas ready (waiting...)"
    fi
else
    print_status 1 "Not found"
fi

# Check Redis
echo -n "Redis StatefulSet: "
if kubectl get statefulset redis -n $NAMESPACE &> /dev/null; then
    READY=$(kubectl get statefulset redis -n $NAMESPACE -o jsonpath='{.status.readyReplicas}')
    DESIRED=$(kubectl get statefulset redis -n $NAMESPACE -o jsonpath='{.status.replicas}')
    if [ "$READY" == "$DESIRED" ]; then
        print_status 0 "$READY/$DESIRED replicas ready"
    else
        print_status 1 "$READY/$DESIRED replicas ready (waiting...)"
    fi
else
    print_status 1 "Not found"
fi

# Check Trading Engine
echo -n "Trading Engine Deployment: "
if kubectl get deployment trading-engine -n $NAMESPACE &> /dev/null; then
    READY=$(kubectl get deployment trading-engine -n $NAMESPACE -o jsonpath='{.status.readyReplicas}')
    DESIRED=$(kubectl get deployment trading-engine -n $NAMESPACE -o jsonpath='{.status.replicas}')
    if [ "$READY" == "$DESIRED" ]; then
        print_status 0 "$READY/$DESIRED replicas ready"
    else
        print_status 1 "$READY/$DESIRED replicas ready (waiting...)"
    fi
else
    print_status 1 "Not found"
fi

echo ""
echo "Checking pods..."

# Get all pods
PODS=$(kubectl get pods -n $NAMESPACE -o json)
TOTAL_PODS=$(echo "$PODS" | jq -r '.items | length')
RUNNING_PODS=$(echo "$PODS" | jq -r '[.items[] | select(.status.phase=="Running")] | length')

echo "Total pods: $TOTAL_PODS"
echo "Running pods: $RUNNING_PODS"

# Check individual pod status
kubectl get pods -n $NAMESPACE -o custom-columns=NAME:.metadata.name,STATUS:.status.phase,READY:.status.containerStatuses[0].ready,RESTARTS:.status.containerStatuses[0].restartCount

echo ""
echo "Checking services..."

# Check services
SERVICES=$(kubectl get services -n $NAMESPACE -o json)

# Check Trading Engine Service
if echo "$SERVICES" | jq -e '.items[] | select(.metadata.name=="trading-engine-service")' &> /dev/null; then
    SERVICE_TYPE=$(echo "$SERVICES" | jq -r '.items[] | select(.metadata.name=="trading-engine-service") | .spec.type')
    print_status 0 "Trading Engine Service ($SERVICE_TYPE)"

    if [ "$SERVICE_TYPE" == "LoadBalancer" ]; then
        LB_IP=$(kubectl get svc trading-engine-service -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
        if [ -z "$LB_IP" ]; then
            LB_IP=$(kubectl get svc trading-engine-service -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
        fi

        if [ ! -z "$LB_IP" ]; then
            echo "  LoadBalancer IP/Hostname: $LB_IP"
        else
            print_warning "LoadBalancer IP not yet assigned (may take a few minutes)"
        fi
    fi
else
    print_status 1 "Trading Engine Service not found"
fi

# Check PostgreSQL Service
if echo "$SERVICES" | jq -e '.items[] | select(.metadata.name=="postgres-service")' &> /dev/null; then
    print_status 0 "PostgreSQL Service"
else
    print_status 1 "PostgreSQL Service not found"
fi

# Check Redis Service
if echo "$SERVICES" | jq -e '.items[] | select(.metadata.name=="redis-service")' &> /dev/null; then
    print_status 0 "Redis Service"
else
    print_status 1 "Redis Service not found"
fi

echo ""
echo "Checking ConfigMaps and Secrets..."

# Check ConfigMap
if kubectl get configmap trading-config -n $NAMESPACE &> /dev/null; then
    print_status 0 "ConfigMap: trading-config"
else
    print_status 1 "ConfigMap: trading-config not found"
fi

# Check Secrets
if kubectl get secret trading-secrets -n $NAMESPACE &> /dev/null; then
    print_status 0 "Secret: trading-secrets"

    # Verify required secret keys
    SECRET_KEYS=$(kubectl get secret trading-secrets -n $NAMESPACE -o jsonpath='{.data}' | jq -r 'keys[]')
    REQUIRED_KEYS=("database-url" "redis-url" "exchange-api-key" "exchange-api-secret" "openrouter-api-key")

    for key in "${REQUIRED_KEYS[@]}"; do
        if echo "$SECRET_KEYS" | grep -q "^$key$"; then
            echo "  ✓ $key"
        else
            print_warning "$key missing in secret"
        fi
    done
else
    print_status 1 "Secret: trading-secrets not found"
    echo "  Please create secrets using: kubectl create secret generic trading-secrets ..."
fi

echo ""
echo "Testing endpoints..."

# Get LoadBalancer IP
LB_IP=$(kubectl get svc trading-engine-service -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
if [ -z "$LB_IP" ]; then
    LB_IP=$(kubectl get svc trading-engine-service -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
fi

if [ ! -z "$LB_IP" ]; then
    echo "Testing endpoints on $LB_IP..."

    # Test /health
    if curl -f -s -o /dev/null -w "%{http_code}" "http://$LB_IP/health" | grep -q "200"; then
        print_status 0 "/health endpoint"
    else
        print_status 1 "/health endpoint not responding"
    fi

    # Test /ready
    if curl -f -s -o /dev/null -w "%{http_code}" "http://$LB_IP/ready" | grep -q "200"; then
        print_status 0 "/ready endpoint"
    else
        print_status 1 "/ready endpoint not responding"
    fi

    # Test /live
    if curl -f -s -o /dev/null -w "%{http_code}" "http://$LB_IP/live" | grep -q "200"; then
        print_status 0 "/live endpoint"
    else
        print_status 1 "/live endpoint not responding"
    fi

    # Test /metrics
    if curl -f -s -o /dev/null -w "%{http_code}" "http://$LB_IP/metrics" | grep -q "200"; then
        print_status 0 "/metrics endpoint"
    else
        print_status 1 "/metrics endpoint not responding"
    fi
else
    print_warning "LoadBalancer IP not available yet. Skipping endpoint tests."
    echo "Run this script again once LoadBalancer IP is assigned."
fi

echo ""
echo "Checking recent events..."
kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp' | tail -10

echo ""
echo "============================================"
echo "Verification Complete"
echo "============================================"

# Summary
ALL_PODS_RUNNING=$((RUNNING_PODS == TOTAL_PODS))
SERVICES_OK=$(kubectl get services -n $NAMESPACE | wc -l)

if [ $ALL_PODS_RUNNING -eq 1 ] && [ $SERVICES_OK -ge 3 ]; then
    echo -e "${GREEN}✅ Deployment appears healthy!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Monitor Grafana dashboards"
    echo "2. Check application logs: kubectl logs -f deployment/trading-engine -n $NAMESPACE"
    echo "3. Run paper trading validation for 7 days"
    echo "4. Review metrics at: http://$LB_IP/metrics"
    exit 0
else
    echo -e "${YELLOW}⚠️  Deployment has some issues. Review the output above.${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "1. Check pod logs: kubectl logs <pod-name> -n $NAMESPACE"
    echo "2. Describe pod: kubectl describe pod <pod-name> -n $NAMESPACE"
    echo "3. Check events: kubectl get events -n $NAMESPACE"
    exit 1
fi
