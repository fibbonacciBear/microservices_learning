#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVICES_DIR="$PROJECT_ROOT/microservices-k8s"

echo "=== Phase 3: Deploy Pizza Shop to Kubernetes ==="
echo ""

# 1. Verify minikube is running
echo "--- Checking minikube status ---"
if ! minikube status --format='{{.Host}}' 2>/dev/null | grep -q Running; then
    echo "Starting minikube..."
    minikube start --driver=docker
fi
echo "minikube is running."
echo ""

# 2. Enable required addons
echo "--- Enabling addons ---"
minikube addons enable ingress 2>/dev/null || true
minikube addons enable metrics-server 2>/dev/null || true
echo "Addons enabled: ingress, metrics-server"
echo ""

# 3. Build Docker images
echo "--- Building Docker images ---"
docker build -t pizza-menu-service:latest "$SERVICES_DIR/menu-service"
docker build -t pizza-order-service:latest "$SERVICES_DIR/order-service"
docker build -t pizza-kitchen-service:latest "$SERVICES_DIR/kitchen-service"
docker build -t pizza-notification-service:latest "$SERVICES_DIR/notification-service"
docker build -t pizza-gateway:latest "$SERVICES_DIR/gateway"
docker build -t pizza-frontend:latest -f "$SERVICES_DIR/gateway/Dockerfile.frontend" "$SERVICES_DIR/gateway"
echo "All 6 images built."
echo ""

# 4. Load images into minikube
echo "--- Loading images into minikube ---"
minikube image load pizza-menu-service:latest
minikube image load pizza-order-service:latest
minikube image load pizza-kitchen-service:latest
minikube image load pizza-notification-service:latest
minikube image load pizza-gateway:latest
minikube image load pizza-frontend:latest
echo "All images loaded into minikube."
echo ""

# 5. Apply Kubernetes manifests
echo "--- Applying Kubernetes manifests ---"
kubectl apply -f "$SCRIPT_DIR/configmap.yaml"
kubectl apply -f "$SCRIPT_DIR/secret.yaml"
kubectl apply -f "$SCRIPT_DIR/menu/deployment.yaml"
kubectl apply -f "$SCRIPT_DIR/menu/service.yaml"
kubectl apply -f "$SCRIPT_DIR/orders/deployment.yaml"
kubectl apply -f "$SCRIPT_DIR/orders/service.yaml"
kubectl apply -f "$SCRIPT_DIR/kitchen/deployment.yaml"
kubectl apply -f "$SCRIPT_DIR/kitchen/service.yaml"
kubectl apply -f "$SCRIPT_DIR/notifications/deployment.yaml"
kubectl apply -f "$SCRIPT_DIR/notifications/service.yaml"
kubectl apply -f "$SCRIPT_DIR/notifications/hpa.yaml"
kubectl apply -f "$SCRIPT_DIR/frontend/deployment.yaml"
kubectl apply -f "$SCRIPT_DIR/frontend/service.yaml"
kubectl apply -f "$SCRIPT_DIR/ingress.yaml"
echo "All manifests applied."
echo ""

# 6. Wait for deployments to be ready
echo "--- Waiting for deployments to be ready ---"
kubectl rollout status deployment/menu-service --timeout=120s
kubectl rollout status deployment/order-service --timeout=120s
kubectl rollout status deployment/kitchen-service --timeout=120s
kubectl rollout status deployment/notification-service --timeout=120s
kubectl rollout status deployment/frontend --timeout=120s
echo ""

# 7. Show status
echo "=== Deployment Complete ==="
echo ""
kubectl get pods
echo ""
kubectl get services
echo ""
kubectl get ingress
echo ""

echo "=== Next Steps ==="
echo "1. Run 'minikube tunnel' in a separate terminal (requires sudo)"
echo "2. Add this line to /etc/hosts if not already present:"
echo "   127.0.0.1 pizza.local"
echo "3. Open http://pizza.local/ in your browser"
echo ""
echo "To run tests:"
echo "   cd $SERVICES_DIR"
echo "   BASE_URL=http://pizza.local/api ORCHESTRATOR=k8s pytest tests/"
