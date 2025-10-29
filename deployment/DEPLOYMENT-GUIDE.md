# Production Deployment Guide - LLM Crypto Trading System

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Infrastructure Setup](#infrastructure-setup)
3. [Kubernetes Deployment](#kubernetes-deployment)
4. [CI/CD Pipeline Setup](#cicd-pipeline-setup)
5. [Monitoring Setup](#monitoring-setup)
6. [Security Hardening](#security-hardening)
7. [Deployment Process](#deployment-process)
8. [Rollback Procedures](#rollback-procedures)
9. [Troubleshooting](#troubleshooting)
10. [Maintenance](#maintenance)

---

## Prerequisites

### Required Tools
- Kubernetes cluster (v1.28+)
- kubectl CLI (v1.28+)
- Helm (v3.12+)
- Docker (v24+)
- GitHub CLI (optional)
- AWS CLI (if using AWS)

### Required Services
- Container Registry (GitHub Container Registry or Docker Hub)
- PostgreSQL (v15+)
- Redis (v7+)
- Prometheus & Grafana (for monitoring)
- SSL certificates (Let's Encrypt recommended)

### Required Secrets
Before deployment, ensure you have:
- Exchange API credentials (Bybit/Binance)
- OpenRouter API key
- Database credentials
- SMTP credentials for alerting
- Slack webhook URL (optional)

---

## Infrastructure Setup

### 1. Kubernetes Cluster Setup

#### AWS EKS (Recommended)
```bash
# Create EKS cluster
eksctl create cluster \
  --name llm-trader-prod \
  --region us-east-1 \
  --nodegroup-name standard-workers \
  --node-type t3.large \
  --nodes 3 \
  --nodes-min 2 \
  --nodes-max 5 \
  --managed

# Configure kubectl
aws eks update-kubeconfig --name llm-trader-prod --region us-east-1
```

#### Digital Ocean Kubernetes
```bash
# Create cluster via DO CLI
doctl kubernetes cluster create llm-trader-prod \
  --region nyc1 \
  --node-pool "name=standard;size=s-2vcpu-4gb;count=3"

# Configure kubectl
doctl kubernetes cluster kubeconfig save llm-trader-prod
```

### 2. Install Required Components

```bash
# Install NGINX Ingress Controller
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace

# Install cert-manager for SSL
helm repo add jetstack https://charts.jetstack.io
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --set installCRDs=true

# Install Prometheus & Grafana
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace
```

---

## Kubernetes Deployment

### 1. Create Namespaces

```bash
kubectl apply -f deployment/kubernetes/namespace.yaml
```

### 2. Configure Secrets

```bash
# Edit secrets file with real values
cp deployment/kubernetes/secrets.yaml deployment/kubernetes/secrets-prod.yaml
# Edit secrets-prod.yaml with actual credentials

# Apply secrets
kubectl apply -f deployment/kubernetes/secrets-prod.yaml
```

### 3. Deploy Infrastructure Components

```bash
# Deploy storage classes and PVCs
kubectl apply -f deployment/kubernetes/storage.yaml

# Deploy PostgreSQL
kubectl apply -f deployment/kubernetes/postgres.yaml

# Wait for PostgreSQL to be ready
kubectl wait --for=condition=ready pod -l component=postgres -n llm-trader-prod --timeout=300s

# Deploy Redis
kubectl apply -f deployment/kubernetes/redis.yaml

# Wait for Redis to be ready
kubectl wait --for=condition=ready pod -l component=redis -n llm-trader-prod --timeout=300s
```

### 4. Deploy Application

```bash
# Apply ConfigMaps
kubectl apply -f deployment/kubernetes/configmap.yaml

# Apply RBAC
kubectl apply -f deployment/kubernetes/rbac.yaml

# Deploy services
kubectl apply -f deployment/kubernetes/services.yaml

# Deploy application
kubectl apply -f deployment/kubernetes/deployment.yaml

# Apply ingress rules
kubectl apply -f deployment/kubernetes/ingress.yaml
```

### 5. Verify Deployment

```bash
# Check pod status
kubectl get pods -n llm-trader-prod

# Check services
kubectl get svc -n llm-trader-prod

# Check ingress
kubectl get ingress -n llm-trader-prod

# View logs
kubectl logs -f deployment/llm-trader-app -n llm-trader-prod
```

---

## CI/CD Pipeline Setup

### 1. GitHub Actions Setup

```bash
# Set GitHub secrets
gh secret set PROD_KUBE_CONFIG < ~/.kube/config
gh secret set STAGING_KUBE_CONFIG < ~/.kube/staging-config
gh secret set SLACK_WEBHOOK --body "https://hooks.slack.com/..."

# Enable GitHub Actions
gh workflow enable ci-cd.yml
gh workflow enable tests.yml
```

### 2. Container Registry Setup

```bash
# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Build and push initial image
docker build -t ghcr.io/[username]/llm-trader:latest .
docker push ghcr.io/[username]/llm-trader:latest
```

### 3. Deployment Triggers

- **Automatic Staging Deploy**: Push to `develop` branch
- **Automatic Production Deploy**: Create GitHub release
- **Manual Deploy**: Use GitHub Actions UI

---

## Monitoring Setup

### 1. Configure Prometheus

```bash
# Apply Prometheus configuration
kubectl apply -f deployment/monitoring/prometheus-config.yaml

# Restart Prometheus to load new config
kubectl rollout restart deployment/prometheus-server -n monitoring
```

### 2. Import Grafana Dashboards

```bash
# Get Grafana admin password
kubectl get secret --namespace monitoring monitoring-grafana -o jsonpath="{.data.admin-password}" | base64 --decode

# Port forward to access Grafana
kubectl port-forward -n monitoring svc/monitoring-grafana 3000:80

# Access Grafana at http://localhost:3000
# Import dashboard from deployment/monitoring/grafana-dashboards/trading-overview.json
```

### 3. Configure Alerts

```bash
# Configure Alertmanager
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: alertmanager-config
  namespace: monitoring
data:
  alertmanager.yml: |
    global:
      slack_api_url: '$SLACK_WEBHOOK_URL'
    route:
      group_by: ['alertname', 'cluster', 'service']
      group_wait: 10s
      group_interval: 10s
      repeat_interval: 12h
      receiver: 'slack-notifications'
    receivers:
    - name: 'slack-notifications'
      slack_configs:
      - channel: '#trading-alerts'
        title: 'LLM Trader Alert'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
EOF
```

---

## Security Hardening

### 1. Network Policies

```bash
# Apply network policies
kubectl apply -f deployment/kubernetes/ingress.yaml
```

### 2. Secret Management

```bash
# Use Sealed Secrets for GitOps
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.18.0/controller.yaml

# Encrypt secrets
kubeseal --format=yaml < secrets.yaml > sealed-secrets.yaml
```

### 3. Security Scanning

```bash
# Run security scan on cluster
kubectl apply -f https://raw.githubusercontent.com/aquasecurity/trivy-operator/main/deploy/static/trivy-operator.yaml

# Check vulnerabilities
kubectl get vulnerabilities -A
```

---

## Deployment Process

### Initial Production Deployment

```bash
# 1. Tag release
git tag -a v1.0.0 -m "Initial production release"
git push origin v1.0.0

# 2. Create GitHub release
gh release create v1.0.0 --title "Production Release v1.0.0" --notes "Initial production deployment"

# 3. Monitor deployment
kubectl get pods -n llm-trader-prod -w

# 4. Run smoke tests
./scripts/smoke-tests.sh production

# 5. Monitor logs
kubectl logs -f deployment/llm-trader-app -n llm-trader-prod
```

### Regular Updates

```bash
# 1. Update code
git checkout main
git pull origin main

# 2. Create release
gh release create v1.0.1 --title "Patch Release v1.0.1" --notes "Bug fixes and improvements"

# 3. CI/CD will automatically deploy

# 4. Verify deployment
kubectl rollout status deployment/llm-trader-app -n llm-trader-prod
```

---

## Rollback Procedures

### Automatic Rollback

The CI/CD pipeline includes automatic rollback on failure:
```yaml
# In .github/workflows/ci-cd.yml
if: failure()
run: |
  kubectl rollout undo deployment/llm-trader-app -n llm-trader-prod
  kubectl rollout status deployment/llm-trader-app -n llm-trader-prod
```

### Manual Rollback

```bash
# View rollout history
kubectl rollout history deployment/llm-trader-app -n llm-trader-prod

# Rollback to previous version
kubectl rollout undo deployment/llm-trader-app -n llm-trader-prod

# Rollback to specific revision
kubectl rollout undo deployment/llm-trader-app -n llm-trader-prod --to-revision=2

# Verify rollback
kubectl get pods -n llm-trader-prod
kubectl rollout status deployment/llm-trader-app -n llm-trader-prod
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. Pods Not Starting
```bash
# Check pod events
kubectl describe pod [pod-name] -n llm-trader-prod

# Check logs
kubectl logs [pod-name] -n llm-trader-prod --previous

# Common causes:
# - Image pull errors: Check registry credentials
# - Resource limits: Increase memory/CPU limits
# - Init container failures: Check database connectivity
```

#### 2. Database Connection Issues
```bash
# Test database connectivity
kubectl run -it --rm debug --image=postgres:15 --restart=Never -n llm-trader-prod -- psql -h postgres-service -U llm_trader_user -d llm_trader

# Check database pod
kubectl logs postgres-0 -n llm-trader-prod
```

#### 3. WebSocket Connection Issues
```bash
# Check WebSocket health
curl -X GET http://api.llm-trader.example.com/health/ready | jq .websocket

# Check network policies
kubectl get networkpolicies -n llm-trader-prod
```

#### 4. High Memory/CPU Usage
```bash
# Check resource usage
kubectl top pods -n llm-trader-prod

# Scale deployment
kubectl scale deployment llm-trader-app --replicas=4 -n llm-trader-prod

# Adjust resource limits
kubectl edit deployment llm-trader-app -n llm-trader-prod
```

---

## Maintenance

### Daily Tasks
- Monitor Grafana dashboards
- Check alert notifications
- Review error logs
- Verify backup completion

### Weekly Tasks
- Review performance metrics
- Update dependencies (if needed)
- Run security scans
- Test disaster recovery

### Monthly Tasks
- SSL certificate renewal (automated with cert-manager)
- Database maintenance and optimization
- Review and rotate API keys
- Performance tuning based on metrics

### Database Backup

```bash
# Manual backup
kubectl exec -it postgres-0 -n llm-trader-prod -- pg_dump -U llm_trader_user llm_trader > backup_$(date +%Y%m%d).sql

# Automated backup (CronJob)
kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: llm-trader-prod
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: postgres-backup
            image: postgres:15
            command:
            - /bin/bash
            - -c
            - |
              pg_dump -h postgres-service -U \$POSTGRES_USER \$POSTGRES_DB | gzip > /backup/db_\$(date +%Y%m%d_%H%M%S).gz
            env:
            - name: POSTGRES_USER
              valueFrom:
                secretKeyRef:
                  name: llm-trader-secrets
                  key: DATABASE_USER
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: llm-trader-secrets
                  key: DATABASE_PASSWORD
            - name: POSTGRES_DB
              value: llm_trader
            volumeMounts:
            - name: backup
              mountPath: /backup
          volumes:
          - name: backup
            persistentVolumeClaim:
              claimName: backup-pvc
          restartPolicy: OnFailure
EOF
```

### Monitoring Checklist

- [ ] System uptime > 99.5%
- [ ] API response time < 2s p95
- [ ] Cache hit rate > 50%
- [ ] Error rate < 0.1%
- [ ] Database connections healthy
- [ ] Redis memory usage < 80%
- [ ] WebSocket connected
- [ ] No critical alerts in last 24h

---

## Emergency Contacts

- **DevOps Lead**: [Contact Info]
- **Database Admin**: [Contact Info]
- **Security Team**: [Contact Info]
- **On-Call Schedule**: [PagerDuty Link]

---

## Appendix

### Useful Commands

```bash
# Get all resources in namespace
kubectl get all -n llm-trader-prod

# Describe deployment
kubectl describe deployment llm-trader-app -n llm-trader-prod

# Execute command in pod
kubectl exec -it [pod-name] -n llm-trader-prod -- /bin/bash

# Copy files from pod
kubectl cp llm-trader-prod/[pod-name]:/app/logs/error.log ./error.log

# Port forwarding for debugging
kubectl port-forward svc/llm-trader-service 8080:80 -n llm-trader-prod

# View resource usage
kubectl top nodes
kubectl top pods -n llm-trader-prod

# Get events
kubectl get events -n llm-trader-prod --sort-by='.lastTimestamp'
```

### Environment Variables Reference

See `deployment/kubernetes/configmap.yaml` for complete list of configuration options.

### Metrics Reference

Key metrics to monitor:
- `trading_decisions_total` - Total trading decisions made
- `portfolio_total_value_usdt` - Current portfolio value
- `portfolio_exposure_ratio` - Risk exposure percentage
- `position_drift_percentage` - Position reconciliation drift
- `llm_request_duration_seconds` - LLM API response time
- `cache_hit_rate` - Cache effectiveness
- `websocket_connection_status` - Exchange connection health

---

**Last Updated**: October 29, 2025
**Version**: 1.0.0
