#!/usr/bin/env bash
set -euo pipefail

# Usage: ./k8s/deploy.sh <image> <namespace> <experience-id>
IMAGE=$1
NAMESPACE=$2
EXPERIENCE_ID=${3:-"none"}
GIT_SHA=${4:-"unknown"}

echo "Deploying to namespace: $NAMESPACE"
echo "Image: $IMAGE"
echo "Experience ID: $EXPERIENCE_ID"

# Replace image placeholder in deployment manifest
sed "s|IMAGE_PLACEHOLDER|${IMAGE}|g" k8s/deployment.yaml > /tmp/deployment.yaml

# Add experience ID labels if present
if [ "$EXPERIENCE_ID" != "none" ] && [ "$EXPERIENCE_ID" != "" ]; then
  # Patch labels into the deployment and pod template
  kubectl apply -f /tmp/deployment.yaml -n "$NAMESPACE"

  kubectl label deployment platform-demo \
    experience-id="$EXPERIENCE_ID" \
    git-sha="$GIT_SHA" \
    --overwrite -n "$NAMESPACE"

  kubectl patch deployment platform-demo -n "$NAMESPACE" --type=json \
    -p="[{\"op\":\"add\",\"path\":\"/spec/template/metadata/labels/experience-id\",\"value\":\"${EXPERIENCE_ID}\"},{\"op\":\"add\",\"path\":\"/spec/template/metadata/labels/git-sha\",\"value\":\"${GIT_SHA}\"}]"
else
  kubectl apply -f /tmp/deployment.yaml -n "$NAMESPACE"
fi

# Apply the service
kubectl apply -f k8s/service.yaml -n "$NAMESPACE"

# Wait for rollout
echo "Waiting for rollout to complete..."
kubectl rollout status deployment/platform-demo -n "$NAMESPACE" --timeout=120s

# Get the service URL
echo "Getting service endpoint..."
for i in $(seq 1 30); do
  EXTERNAL_IP=$(kubectl get svc platform-demo -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
  if [ -n "$EXTERNAL_IP" ]; then
    echo "Service available at: http://${EXTERNAL_IP}/api/products"
    break
  fi
  echo "Waiting for external IP... ($i/30)"
  sleep 10
done