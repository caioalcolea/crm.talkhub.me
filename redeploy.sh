#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# TalkHub CRM — Redeploy Limpo
# Remove stacks → prune → rebuild → redeploy
#
# Uso:
#   ./redeploy.sh              # Redeploy normal (preserva dados)
#   ./redeploy.sh --clean-db   # Recria volumes do banco (APAGA DADOS)
#   ./redeploy.sh --clean-all  # Recria TODOS os volumes (APAGA TUDO)
# ============================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${CYAN}[$(date '+%H:%M:%S')]${NC} $*"; }
ok()   { echo -e "${GREEN}[$(date '+%H:%M:%S')] ✔${NC} $*"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] ⚠${NC} $*"; }
fail() { echo -e "${RED}[$(date '+%H:%M:%S')] ✘${NC} $*"; exit 1; }

STACK_NAME="djangocrm"
COMPOSE_FILE="docker/djangocrm.yaml"
BACKEND_IMAGE="talkhub/djangocrm-backend:latest"
FRONTEND_IMAGE="talkhub/djangocrm-frontend:latest"
API_URL="${PUBLIC_DJANGO_API_URL:-https://crm.talkhub.me}"

# Source environment variables
ENV_FILE="docker/.env"
if [[ -f "$ENV_FILE" ]]; then
    set -a
    source "$ENV_FILE"
    set +a
    ok "Environment loaded from $ENV_FILE"
else
    fail "Environment file not found: $ENV_FILE — copy docker/.env.example to docker/.env and fill in values"
fi

SLEEP_SECONDS=15

# ============================================================
# Parse argumentos
# ============================================================
CLEAN_DB=false
CLEAN_ALL=false

for arg in "$@"; do
    case "$arg" in
        --clean-db)  CLEAN_DB=true ;;
        --clean-all) CLEAN_ALL=true ;;
        --help|-h)
            echo "Uso: ./redeploy.sh [--clean-db | --clean-all]"
            echo ""
            echo "  --clean-db   Remove e recria volume do banco (APAGA DADOS)"
            echo "  --clean-all  Remove e recria TODOS os volumes (APAGA TUDO)"
            echo ""
            exit 0
            ;;
        *) fail "Argumento desconhecido: $arg (use --help)" ;;
    esac
done

# Verifica se está na raiz do projeto
[[ -f "$COMPOSE_FILE" ]] || fail "Execute este script da raiz do repositório (crmtalkhub/)"

# Verifica se Docker Swarm está ativo
docker info --format '{{.Swarm.LocalNodeState}}' 2>/dev/null | grep -q "active" \
    || fail "Docker Swarm não está ativo. Execute: docker swarm init"

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║       TalkHub CRM — Redeploy Limpo              ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════╝${NC}"
echo ""

if $CLEAN_ALL; then
    warn "Modo --clean-all: TODOS os volumes serão recriados (dados perdidos)"
elif $CLEAN_DB; then
    warn "Modo --clean-db: Volume do banco será recriado (dados perdidos)"
fi

# ============================================================
# 1. Remover stack do CRM
# ============================================================
log "1/6 — Removendo stack '${STACK_NAME}'..."

if docker stack ls --format '{{.Name}}' | grep -q "^${STACK_NAME}$"; then
    docker stack rm "$STACK_NAME"
    ok "Stack '${STACK_NAME}' removida"
else
    warn "Stack '${STACK_NAME}' não encontrada (pulando)"
fi

# ============================================================
# 2. Aguardar containers pararem
# ============================================================
log "2/6 — Aguardando ${SLEEP_SECONDS}s para containers finalizarem..."
sleep "$SLEEP_SECONDS"

# Espera extra: garante que nenhum container da stack está rodando
RETRIES=0
while docker ps -q --filter "label=com.docker.stack.namespace=${STACK_NAME}" | grep -q .; do
    RETRIES=$((RETRIES + 1))
    if [[ $RETRIES -ge 12 ]]; then
        warn "Timeout esperando containers pararem — continuando mesmo assim"
        break
    fi
    log "  Containers ainda rodando, aguardando mais 5s... (tentativa ${RETRIES}/12)"
    sleep 5
done
ok "Containers finalizados"

# ============================================================
# 3. Gerenciar volumes (limpar se solicitado)
# ============================================================
log "3/6 — Gerenciando volumes..."

ALL_VOLUMES=(crm_db crm_static crm_media crm_redis)
DB_VOLUMES=(crm_db)

if $CLEAN_ALL; then
    # Remover e recriar TODOS os volumes
    for vol in "${ALL_VOLUMES[@]}"; do
        docker volume rm "$vol" 2>/dev/null && ok "Volume '${vol}' removido" || true
    done
    for vol in "${ALL_VOLUMES[@]}"; do
        docker volume create "$vol"
        ok "Volume '${vol}' criado (limpo)"
    done
elif $CLEAN_DB; then
    # Remover e recriar apenas o volume do banco
    for vol in "${DB_VOLUMES[@]}"; do
        docker volume rm "$vol" 2>/dev/null && ok "Volume '${vol}' removido" || true
    done
    for vol in "${DB_VOLUMES[@]}"; do
        docker volume create "$vol"
        ok "Volume '${vol}' criado (limpo)"
    done
    # Garantir que os outros volumes existem
    for vol in crm_static crm_media crm_redis; do
        docker volume inspect "$vol" &>/dev/null || {
            docker volume create "$vol"
            ok "Volume '${vol}' criado"
        }
    done
else
    # Modo normal: apenas garantir que existem
    for vol in "${ALL_VOLUMES[@]}"; do
        docker volume inspect "$vol" &>/dev/null || {
            docker volume create "$vol"
            ok "Volume '${vol}' criado"
        }
    done
fi

# ============================================================
# 4. Prune (containers, imagens, networks, build cache)
# ============================================================
log "4/6 — Executando prune do Docker..."
docker container prune -f 2>/dev/null || true
docker image prune -f 2>/dev/null || true
docker network prune -f 2>/dev/null || true
docker builder prune -f 2>/dev/null || true
ok "Prune concluído"

# ============================================================
# 5. Rebuild das imagens
# ============================================================
log "5/6 — Rebuild das imagens..."

log "  [backend] Construindo ${BACKEND_IMAGE}..."
docker build \
    --no-cache \
    -t "$BACKEND_IMAGE" \
    -f docker/Dockerfile.backend \
    . \
    || fail "Falha no build do backend"
ok "Backend build concluído"

log "  [frontend] Construindo ${FRONTEND_IMAGE}..."
docker build \
    --no-cache \
    -t "$FRONTEND_IMAGE" \
    -f docker/Dockerfile.frontend \
    --build-arg PUBLIC_DJANGO_API_URL="$API_URL" \
    djangocrm/frontend/ \
    || fail "Falha no build do frontend"
ok "Frontend build concluído"

# ============================================================
# 6. Garantir rede externa e deploy da stack
# ============================================================
log "6/6 — Deploy da stack '${STACK_NAME}'..."

# Criar rede externa se não existir
docker network inspect talkhub &>/dev/null || {
    docker network create --driver overlay --attachable talkhub
    ok "Rede 'talkhub' criada"
}

docker stack deploy -c "$COMPOSE_FILE" "$STACK_NAME"
ok "Stack '${STACK_NAME}' deployada"

# ============================================================
# Resumo
# ============================================================
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       Redeploy concluído com sucesso!            ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
log "Serviços:"
docker stack services "$STACK_NAME" --format "  {{.Name}}\t{{.Replicas}}\t{{.Image}}" 2>/dev/null || true
echo ""

if $CLEAN_DB || $CLEAN_ALL; then
    warn "Banco recriado do zero — migrations serão aplicadas automaticamente pelo entrypoint"
    log "O entrypoint vai executar: migrate → manage_rls --status → collectstatic → create_default_admin"
    echo ""
fi

log "Acompanhe os logs com:"
echo "  docker service logs -f ${STACK_NAME}_crm_backend"
echo "  docker service logs -f ${STACK_NAME}_crm_frontend"
echo ""
