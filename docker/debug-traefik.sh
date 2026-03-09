#!/bin/bash
# TalkHub CRM — Debug Traefik routing issues
# Run: bash docker/debug-traefik.sh

echo "=== 1. Traefik service status ==="
docker service ls --filter name=traefik
echo ""

echo "=== 2. CRM services status ==="
docker service ls --filter label=com.docker.stack.namespace=djangocrm
echo ""

echo "=== 3. Traefik networks ==="
TRAEFIK_ID=$(docker service ls -q --filter name=traefik)
docker service inspect "$TRAEFIK_ID" --format '{{range .Spec.TaskTemplate.Networks}}Network: {{.Target}}{{"\n"}}{{end}}' 2>/dev/null
echo ""

echo "=== 4. talkhub network ID ==="
docker network inspect talkhub --format '{{.Id}}' 2>/dev/null
echo ""

echo "=== 5. Is Traefik on the talkhub network? ==="
TALKHUB_NET=$(docker network inspect talkhub --format '{{.Id}}' 2>/dev/null)
TRAEFIK_NETS=$(docker service inspect "$TRAEFIK_ID" --format '{{range .Spec.TaskTemplate.Networks}}{{.Target}} {{end}}' 2>/dev/null)
if echo "$TRAEFIK_NETS" | grep -q "$TALKHUB_NET"; then
    echo "YES — Traefik is on the talkhub network"
else
    echo "NO — Traefik is NOT on the talkhub network!"
    echo "  Traefik networks: $TRAEFIK_NETS"
    echo "  talkhub network:  $TALKHUB_NET"
    echo ""
    echo "  FIX: docker service update --network-add talkhub $TRAEFIK_ID"
fi
echo ""

echo "=== 6. Backend service labels (deploy labels) ==="
docker service inspect djangocrm_crm_backend --format '{{json .Spec.Labels}}' 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "Service not found"
echo ""

echo "=== 7. Frontend service labels (deploy labels) ==="
docker service inspect djangocrm_crm_frontend --format '{{json .Spec.Labels}}' 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "Service not found"
echo ""

echo "=== 8. Direct backend connectivity test ==="
BACKEND_IP=$(docker service inspect djangocrm_crm_backend --format '{{range .Endpoint.VirtualIPs}}{{.Addr}} {{end}}' 2>/dev/null)
echo "Backend VIP: $BACKEND_IP"
# Test from a container on the talkhub network
docker run --rm --network talkhub alpine:latest wget -qO- --timeout=3 http://djangocrm_crm_backend:8000/health/ 2>&1 || echo "  Could not reach backend on talkhub network"
echo ""

echo "=== 9. Direct frontend connectivity test ==="
docker run --rm --network talkhub alpine:latest wget -qO- --timeout=3 http://djangocrm_crm_frontend:3000/ 2>&1 | head -5 || echo "  Could not reach frontend on talkhub network"
echo ""

echo "=== 10. Traefik logs (last 30 lines) ==="
docker service logs "$TRAEFIK_ID" --tail 30 2>&1 | tail -30
echo ""

echo "=== 11. Traefik API routers check ==="
# Try API on common ports
for port in 8080 8081 9090; do
    RESULT=$(curl -s --connect-timeout 2 http://localhost:$port/api/http/routers 2>/dev/null | head -c 100)
    if [ -n "$RESULT" ]; then
        echo "Traefik API on port $port:"
        curl -s http://localhost:$port/api/http/routers 2>/dev/null | python3 -m json.tool 2>/dev/null | grep -A5 "crm"
        break
    fi
done
echo ""
echo "=== Done ==="
