#!/bin/bash
set -euo pipefail
# TalkHub CRM — Quick fix: clean redeploy (preserves data)
# Removes stack completely to clear stale Traefik labels, then redeploys

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
log()  { echo -e "${CYAN}[$(date '+%H:%M:%S')]${NC} $*"; }
ok()   { echo -e "${GREEN}[$(date '+%H:%M:%S')] OK${NC} $*"; }

cd "$(dirname "$0")/.."

log "1. Removing stack completely (to clear stale Traefik labels)..."
docker stack rm djangocrm 2>/dev/null || true

log "2. Waiting for all containers to stop..."
sleep 10
RETRIES=0
while docker ps -q --filter "label=com.docker.stack.namespace=djangocrm" | grep -q .; do
    RETRIES=$((RETRIES + 1))
    [ $RETRIES -ge 12 ] && { echo "Timeout, continuing..."; break; }
    echo "  Still running, waiting 5s... ($RETRIES/12)"
    sleep 5
done
ok "Containers stopped"

log "3. Ensuring volumes exist..."
for vol in crm_db crm_static crm_media crm_redis; do
    docker volume inspect "$vol" &>/dev/null || docker volume create "$vol"
done
ok "Volumes ready"

log "4. Ensuring talkhub network exists..."
docker network inspect talkhub &>/dev/null || docker network create --driver overlay --attachable talkhub
ok "Network ready"

log "5. Checking service status before deploy..."
docker service ps djangocrm_crm_backend 2>/dev/null && echo "(backend tasks found)" || echo "(no backend tasks — clean slate)"

log "6. Deploying stack..."
docker stack deploy -c docker/djangocrm.yaml djangocrm
ok "Stack deployed"

log "7. Waiting 15s for services to start..."
sleep 15

log "8. Service status:"
docker service ls --filter label=com.docker.stack.namespace=djangocrm
echo ""

log "9. Checking for failures..."
for svc in crm_backend crm_frontend crm_worker crm_beat; do
    REPLICAS=$(docker service ls --filter name=djangocrm_$svc --format '{{.Replicas}}' 2>/dev/null)
    if [ "$REPLICAS" = "0/1" ]; then
        echo ""
        echo -e "${RED}=== djangocrm_$svc FAILED (0/1) ===${NC}"
        docker service ps djangocrm_$svc --no-trunc --format "{{.Error}}" 2>/dev/null | head -3
        echo "Logs:"
        docker service logs djangocrm_$svc --tail 10 2>/dev/null || true
        echo ""
    else
        ok "$svc: $REPLICAS"
    fi
done

echo ""
log "10. Verifying Traefik labels are clean (no stale labels)..."
docker service inspect djangocrm_crm_backend --format '{{json .Spec.Labels}}' 2>/dev/null | python3 -c "
import json,sys
labels = json.load(sys.stdin)
traefik_labels = {k:v for k,v in labels.items() if k.startswith('traefik')}
print(json.dumps(traefik_labels, indent=2))
" 2>/dev/null || echo "Could not read labels"

echo ""
echo -e "${GREEN}Done. If services show 1/1, test: curl -sk https://crm.talkhub.me/health/${NC}"
echo "If still 0/1, check: docker service ps djangocrm_crm_backend --no-trunc"
