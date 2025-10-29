# Kubernetes Deployment Guide

This directory contains all Kubernetes manifests and Helm charts for deploying the LLM-Powered Cryptocurrency Trading System to production.

## 📁 Directory Structure

```
kubernetes/
├── namespace.yaml                    # Namespace, quotas, and limits
├── deployments/
│   ├── trading-engine.yaml          # Main trading engine deployment
│   ├── postgres.yaml                # PostgreSQL + TimescaleDB
│   └── redis.yaml                   # Redis cache
├── services/
│   └── trading-engine-service.yaml  # LoadBalancer and ClusterIP services
├── configmaps/
│   └── app-config.yaml              # Application configuration
├── secrets/
│   └── secrets-template.yaml        # Secrets template (DO NOT commit actual secrets!)
└── helm/
    └── trading-system/              # Helm chart for simplified deployment
        ├── Chart.yaml
        ├── values.yaml
        └── templates/
```

## 🚀 Quick Start

### Prerequisites

1. **Kubernetes Cluster**: Running cluster with kubectl configured
2. **kubectl**: Version 1.28 or higher
3. **Helm**: Version 3.0 or higher (optional, for Helm deployment)
4. **Docker Registry Access**: Access to push/pull container images

### Deployment Steps

#### Option 1: Deploy with kubectl (Recommended for production)

```bash
# 1. Create namespace
kubectl apply -f kubernetes/namespace.yaml

# 2. Create secrets (replace with actual values)
kubectl create secret generic trading-secrets \
  --namespace=trading-system \
  --from-literal=database-url='postgresql://user:SECURE_PASSWORD@postgres-service:5432/trading' \
  --from-literal=redis-url='redis://redis-service:6379/0' \
  --from-literal=exchange-api-key='YOUR_BYBIT_API_KEY' \
  --from-literal=exchange-api-secret='YOUR_BYBIT_API_SECRET' \
  --from-literal=openrouter-api-key='YOUR_OPENROUTER_KEY'

# 3. Apply ConfigMaps
kubectl apply -f kubernetes/configmaps/

# 4. Deploy databases
kubectl apply -f kubernetes/deployments/postgres.yaml
kubectl apply -f kubernetes/deployments/redis.yaml

# Wait for databases to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n trading-system --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n trading-system --timeout=300s

# 5. Deploy trading engine
kubectl apply -f kubernetes/deployments/trading-engine.yaml

# 6. Create services
kubectl apply -f kubernetes/services/

# 7. Verify deployment
kubectl get all -n trading-system
```

#### Option 2: Deploy with Helm

```bash
# 1. Create namespace
kubectl create namespace trading-system

# 2. Create secrets (same as above)

# 3. Install with Helm
helm install trading-system kubernetes/helm/trading-system/ \
  --namespace trading-system \
  --values kubernetes/helm/trading-system/values.yaml

# 4. Verify installation
helm list -n trading-system
kubectl get all -n trading-system
```

## 🔧 Configuration

### Environment Variables (ConfigMap)

Key configuration variables in `kubernetes/configmaps/app-config.yaml`:

```yaml
# Trading mode
TRADING_MODE: "paper"              # Change to "live" for production trading
EXCHANGE_TESTNET: "true"           # Change to "false" for live trading

# Risk management
MAX_POSITION_SIZE_PCT: "0.10"      # 10% max per position
MAX_PORTFOLIO_EXPOSURE: "0.80"     # 80% max total exposure
STOP_LOSS_PCT: "0.05"              # 5% stop loss

# Decision interval
DECISION_INTERVAL: "180"           # 3 minutes (180 seconds)
```

### Secrets Management

**NEVER commit actual secrets to Git!**

Create secrets using kubectl:

```bash
# Create from command line
kubectl create secret generic trading-secrets \
  --namespace=trading-system \
  --from-literal=database-url='postgresql://...' \
  --from-literal=exchange-api-key='...' \
  --dry-run=client -o yaml | kubectl apply -f -

# Or create from file (ensure file is in .gitignore!)
kubectl create secret generic trading-secrets \
  --namespace=trading-system \
  --from-env-file=.secrets.env
```

Required secrets:
- `database-url`: PostgreSQL connection string
- `redis-url`: Redis connection string
- `exchange-api-key`: Bybit API key
- `exchange-api-secret`: Bybit API secret
- `openrouter-api-key`: OpenRouter API key for LLM
- `smtp-password`: Email SMTP password (optional)
- `slack-webhook-url`: Slack webhook URL (optional)
- `pagerduty-api-key`: PagerDuty API key (optional)

## 📊 Monitoring

### Health Checks

The trading engine exposes three health endpoints:

```bash
# Basic health check
curl http://<loadbalancer-ip>/health

# Kubernetes readiness probe
curl http://<loadbalancer-ip>/ready

# Kubernetes liveness probe (detects frozen application)
curl http://<loadbalancer-ip>/live
```

### Prometheus Metrics

Metrics are exposed at `/metrics` endpoint:

```bash
curl http://<loadbalancer-ip>/metrics
```

Configure Prometheus to scrape:

```yaml
scrape_configs:
  - job_name: 'trading-engine'
    kubernetes_sd_configs:
      - role: pod
        namespaces:
          names: [trading-system]
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
```

### Grafana Dashboards

Import dashboards from `grafana/dashboards/`:
- `trading-overview.json` - Trading performance and P&L
- `risk-metrics.json` - Risk management metrics
- `performance.json` - System performance metrics

## 🔄 Deployment Operations

### Rolling Update

```bash
# Update image to new version
kubectl set image deployment/trading-engine \
  trading-engine=trading-engine:v2.0.0 \
  -n trading-system

# Monitor rollout
kubectl rollout status deployment/trading-engine -n trading-system

# Check rollout history
kubectl rollout history deployment/trading-engine -n trading-system
```

### Rollback

```bash
# Rollback to previous version
kubectl rollout undo deployment/trading-engine -n trading-system

# Rollback to specific revision
kubectl rollout undo deployment/trading-engine --to-revision=3 -n trading-system
```

### Scaling

```bash
# Scale replicas
kubectl scale deployment/trading-engine --replicas=5 -n trading-system

# Auto-scaling (requires metrics-server)
kubectl autoscale deployment/trading-engine \
  --min=3 --max=10 \
  --cpu-percent=80 \
  -n trading-system
```

## 🐛 Troubleshooting

### Check Pod Status

```bash
# Get all pods
kubectl get pods -n trading-system

# Describe pod for events
kubectl describe pod <pod-name> -n trading-system

# View logs
kubectl logs <pod-name> -n trading-system

# Follow logs
kubectl logs -f <pod-name> -n trading-system

# View previous crashed container logs
kubectl logs <pod-name> -n trading-system --previous
```

### Debug Networking

```bash
# Check services
kubectl get svc -n trading-system

# Check endpoints
kubectl get endpoints -n trading-system

# Test connectivity from within cluster
kubectl run -it --rm debug --image=busybox --restart=Never -n trading-system -- sh
# Inside pod:
wget -O- http://trading-engine-service/health
```

### Check Resources

```bash
# Top pods (requires metrics-server)
kubectl top pods -n trading-system

# Describe node
kubectl describe node <node-name>

# Check events
kubectl get events -n trading-system --sort-by='.lastTimestamp'
```

### Common Issues

#### 1. Pods not starting (CrashLoopBackOff)

```bash
# Check logs
kubectl logs <pod-name> -n trading-system

# Common causes:
# - Missing secrets
# - Database not ready
# - Configuration errors
```

#### 2. Database connection issues

```bash
# Verify database pod is running
kubectl get pods -l app=postgres -n trading-system

# Test database connection
kubectl exec -it postgres-0 -n trading-system -- psql -U trading_user -d trading
```

#### 3. Service not accessible

```bash
# Check service
kubectl get svc trading-engine-service -n trading-system

# Check if LoadBalancer IP is assigned
kubectl describe svc trading-engine-service -n trading-system

# Check pod labels match service selector
kubectl get pods -l app=trading-engine -n trading-system --show-labels
```

## 🔒 Security Best Practices

### 1. Use Secrets Management

- **DO NOT** commit secrets to Git
- Use Kubernetes Secrets or external secret managers (Vault, AWS Secrets Manager)
- Rotate secrets regularly (every 90 days)

### 2. Network Policies

```bash
# Apply network policies (create kubernetes/network-policies.yaml)
kubectl apply -f kubernetes/network-policies.yaml
```

### 3. RBAC

```bash
# Create service account with minimal permissions
kubectl apply -f kubernetes/rbac.yaml
```

### 4. Pod Security Standards

```yaml
# Already configured in deployment:
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: false
```

## 💾 Backup and Disaster Recovery

### Database Backups

```bash
# Manual backup
kubectl exec postgres-0 -n trading-system -- \
  pg_dump -U trading_user trading > backup-$(date +%Y%m%d).sql

# Restore from backup
cat backup-20250129.sql | \
  kubectl exec -i postgres-0 -n trading-system -- \
  psql -U trading_user trading
```

### Automated Backups (recommended)

Set up CronJob for automated backups:

```yaml
# kubernetes/cronjobs/backup.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: trading-system
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:15
            command:
            - /bin/bash
            - -c
            - pg_dump -U trading_user -h postgres-service trading | gzip > /backup/backup-$(date +\%Y\%m\%d-\%H\%M).sql.gz
            volumeMounts:
            - name: backup
              mountPath: /backup
          restartPolicy: OnFailure
          volumes:
          - name: backup
            persistentVolumeClaim:
              claimName: backup-pvc
```

## 📈 Performance Tuning

### Database Optimization

```bash
# Connect to PostgreSQL
kubectl exec -it postgres-0 -n trading-system -- psql -U trading_user trading

# Check slow queries
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

# Create indexes
CREATE INDEX CONCURRENTLY idx_positions_symbol_status ON positions(symbol, status);
```

### Resource Limits

Adjust in `kubernetes/deployments/trading-engine.yaml`:

```yaml
resources:
  requests:
    memory: "2Gi"    # Guaranteed
    cpu: "1000m"
  limits:
    memory: "4Gi"    # Maximum
    cpu: "2000m"
```

## 🔗 Useful Commands

```bash
# Get LoadBalancer IP
kubectl get svc trading-engine-service -n trading-system \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}'

# Port forward for local access
kubectl port-forward svc/trading-engine-service 8000:80 -n trading-system

# Execute command in pod
kubectl exec -it <pod-name> -n trading-system -- bash

# Copy files from pod
kubectl cp <pod-name>:/app/logs/trading.log ./trading.log -n trading-system

# Delete all resources in namespace
kubectl delete all --all -n trading-system
```

## 📚 Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Helm Documentation](https://helm.sh/docs/)
- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
- [Trading System PRD](../PRD/llm_crypto_trading_prd.md)
- [Sprint 3 Overview](../PRPs/sprints/SPRINT-3-OVERVIEW.md)

## 🆘 Support

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) section
2. Review pod logs: `kubectl logs <pod-name> -n trading-system`
3. Check Grafana dashboards for system health
4. Review GitHub Issues
5. Contact DevOps team

---

**Production Readiness Checklist:**

- [ ] Secrets created and verified
- [ ] Database backups configured
- [ ] Monitoring and alerting set up
- [ ] Resource limits tuned
- [ ] Network policies applied
- [ ] RBAC configured
- [ ] Disaster recovery plan documented
- [ ] Team trained on operations
- [ ] Rollback procedure tested
- [ ] 7-day paper trading validation passed

**Status**: Ready for production deployment ✅
