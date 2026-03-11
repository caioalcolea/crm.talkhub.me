#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# TalkHub CRM — Redeploy Limpo
# Remove stacks → prune → rebuild → redeploy → verify
#
# Uso:
#   ./redeploy.sh              # Redeploy normal (preserva dados)
#   ./redeploy.sh --clean-db   # Recria volumes do banco (APAGA DADOS)
#   ./redeploy.sh --clean-all  # Recria TODOS os volumes (APAGA TUDO)
#   ./redeploy.sh --no-cache   # Rebuild sem cache do Docker (mais lento)
#   ./redeploy.sh --skip-build # Pula rebuild de imagens (usa existentes)
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
COWORK_SERVER_IMAGE="talkhub/cowork-server:latest"
COWORK_APP_IMAGE="talkhub/cowork-app:latest"
API_URL="${PUBLIC_DJANGO_API_URL:-https://crm.talkhub.me}"

# Source environment variables (optional — YAML has inline defaults)
ENV_FILE="docker/.env"
if [[ -f "$ENV_FILE" ]]; then
    set -a
    source "$ENV_FILE"
    set +a
    ok "Environment loaded from $ENV_FILE"
else
    warn "No docker/.env found — using inline defaults from YAML"
fi

SLEEP_SECONDS=15

# ============================================================
# Parse argumentos
# ============================================================
CLEAN_DB=false
CLEAN_ALL=false
NO_CACHE=""
SKIP_BUILD=false

for arg in "$@"; do
    case "$arg" in
        --clean-db)   CLEAN_DB=true ;;
        --clean-all)  CLEAN_ALL=true ;;
        --no-cache)   NO_CACHE="--no-cache" ;;
        --skip-build) SKIP_BUILD=true ;;
        --help|-h)
            echo "Uso: ./redeploy.sh [opções]"
            echo ""
            echo "  --clean-db    Remove e recria volume do banco (APAGA DADOS)"
            echo "  --clean-all   Remove e recria TODOS os volumes (APAGA TUDO)"
            echo "  --no-cache    Build sem cache do Docker (mais lento, mais limpo)"
            echo "  --skip-build  Pula rebuild de imagens (usa existentes)"
            echo ""
            exit 0
            ;;
        *) fail "Argumento desconhecido: $arg (use --help)" ;;
    esac
done

# Verifica se está na raiz do projeto
[[ -f "$COMPOSE_FILE" ]] || fail "Execute este script da raiz do repositório"

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
log "1/7 — Removendo stack '${STACK_NAME}'..."

if docker stack ls --format '{{.Name}}' | grep -q "^${STACK_NAME}$"; then
    docker stack rm "$STACK_NAME"
    ok "Stack '${STACK_NAME}' removida"
else
    warn "Stack '${STACK_NAME}' não encontrada (pulando)"
fi

# ============================================================
# 2. Aguardar containers pararem
# ============================================================
log "2/7 — Aguardando ${SLEEP_SECONDS}s para containers finalizarem..."
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
log "3/7 — Gerenciando volumes..."

ALL_VOLUMES=(crm_db crm_static crm_media crm_redis)
DB_VOLUMES=(crm_db)

if $CLEAN_ALL; then
    for vol in "${ALL_VOLUMES[@]}"; do
        docker volume rm "$vol" 2>/dev/null && ok "Volume '${vol}' removido" || true
    done
    for vol in "${ALL_VOLUMES[@]}"; do
        docker volume create "$vol"
        ok "Volume '${vol}' criado (limpo)"
    done
elif $CLEAN_DB; then
    for vol in "${DB_VOLUMES[@]}"; do
        docker volume rm "$vol" 2>/dev/null && ok "Volume '${vol}' removido" || true
    done
    for vol in "${DB_VOLUMES[@]}"; do
        docker volume create "$vol"
        ok "Volume '${vol}' criado (limpo)"
    done
    for vol in crm_static crm_media crm_redis; do
        docker volume inspect "$vol" &>/dev/null || {
            docker volume create "$vol"
            ok "Volume '${vol}' criado"
        }
    done
else
    for vol in "${ALL_VOLUMES[@]}"; do
        docker volume inspect "$vol" &>/dev/null || {
            docker volume create "$vol"
            ok "Volume '${vol}' criado"
        }
    done
fi

# ============================================================
# 4. Prune (containers, imagens, build cache)
# ============================================================
log "4/7 — Executando prune do Docker..."
docker container prune -f 2>/dev/null || true
docker image prune -f 2>/dev/null || true
# NOT pruning networks — talkhub is shared with other stacks (traefik, etc)
docker builder prune -f 2>/dev/null || true
ok "Prune concluído"

# ============================================================
# 5. Rebuild das imagens
# ============================================================
if $SKIP_BUILD; then
    warn "5/7 — Build pulado (--skip-build)"
else
    log "5/7 — Rebuild das imagens..."

    log "  [backend] Construindo ${BACKEND_IMAGE}..."
    docker build \
        $NO_CACHE \
        -t "$BACKEND_IMAGE" \
        -f docker/Dockerfile.backend \
        . \
        || fail "Falha no build do backend"
    ok "Backend build concluído"

    log "  [frontend] Construindo ${FRONTEND_IMAGE}..."
    docker build \
        $NO_CACHE \
        -t "$FRONTEND_IMAGE" \
        -f docker/Dockerfile.frontend \
        --build-arg PUBLIC_DJANGO_API_URL="$API_URL" \
        . \
        || fail "Falha no build do frontend"
    ok "Frontend build concluído"

    log "  [cowork-server] Construindo ${COWORK_SERVER_IMAGE}..."
    docker build \
        $NO_CACHE \
        -t "$COWORK_SERVER_IMAGE" \
        -f docker/Dockerfile.cowork-server \
        . \
        || fail "Falha no build do cowork-server"
    ok "Cowork server build concluído"

    log "  [cowork-app] Construindo ${COWORK_APP_IMAGE}..."
    docker build \
        $NO_CACHE \
        -t "$COWORK_APP_IMAGE" \
        -f docker/Dockerfile.cowork-app \
        . \
        || fail "Falha no build do cowork-app"
    ok "Cowork app build concluído"
fi

# ============================================================
# 6. Garantir rede externa e deploy da stack
# ============================================================
log "6/7 — Deploy da stack '${STACK_NAME}'..."

# Criar rede externa se não existir
docker network inspect talkhub &>/dev/null || {
    docker network create --driver overlay --attachable talkhub
    ok "Rede 'talkhub' criada"
}

docker stack deploy -c "$COMPOSE_FILE" "$STACK_NAME"
ok "Stack '${STACK_NAME}' deployada"

# ============================================================
# 7. Verificação pós-deploy
# ============================================================
log "7/7 — Verificação pós-deploy..."
log "  Aguardando 20s para serviços iniciarem..."
sleep 20

DEPLOY_OK=true

for svc in crm_backend crm_frontend crm_worker crm_beat crm_db crm_redis crm_cowork_backend crm_cowork_front; do
    REPLICAS=$(docker service ls --filter "name=${STACK_NAME}_${svc}" --format '{{.Replicas}}' 2>/dev/null || echo "?/?")
    if echo "$REPLICAS" | grep -q "0/"; then
        echo -e "  ${RED}✘ ${svc}: ${REPLICAS}${NC}"
        # Mostrar erro do serviço que falhou
        docker service ps "${STACK_NAME}_${svc}" --no-trunc --format "    Error: {{.Error}}" 2>/dev/null | head -2
        DEPLOY_OK=false
    else
        echo -e "  ${GREEN}✔ ${svc}: ${REPLICAS}${NC}"
    fi
done

echo ""

# Aguardar backend estar pronto e verificar migrations
log "  Aguardando backend ficar pronto..."
BACKEND_READY=false
for i in $(seq 1 30); do
    BACKEND_ID=$(docker ps -q -f "name=${STACK_NAME}_crm_backend" 2>/dev/null | head -1)
    if [[ -n "$BACKEND_ID" ]]; then
        # Verificar se o entrypoint terminou (Gunicorn está rodando)
        if docker exec "$BACKEND_ID" python -c "import django; django.setup()" 2>/dev/null; then
            BACKEND_READY=true
            break
        fi
    fi
    sleep 2
done

if $BACKEND_READY; then
    ok "Backend pronto"

    # Verificar migrations pendentes
    log "  Verificando migrations..."
    PENDING=$(docker exec "$BACKEND_ID" python manage.py showmigrations --plan 2>/dev/null | grep "\[ \]" | head -10 || true)
    if [[ -n "$PENDING" ]]; then
        warn "Migrations pendentes encontradas:"
        echo "$PENDING" | head -10
        warn "O entrypoint deveria ter aplicado. Verifique os logs do backend."
    else
        ok "Todas as migrations aplicadas"
    fi

    # Verificar RLS
    log "  Verificando RLS..."
    docker exec "$BACKEND_ID" python manage.py manage_rls --status 2>/dev/null | tail -3 || warn "RLS check falhou"
else
    warn "Backend não ficou pronto em 60s — verifique os logs"
fi

# ============================================================
# Resumo
# ============================================================
echo ""
if $DEPLOY_OK; then
    echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║       Redeploy concluído com sucesso!            ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
else
    echo -e "${RED}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║   Redeploy com problemas — verifique os logs    ║${NC}"
    echo -e "${RED}╚══════════════════════════════════════════════════╝${NC}"
fi
echo ""

if $CLEAN_DB || $CLEAN_ALL; then
    warn "Banco recriado do zero — migrations, RLS, admin foram configurados pelo entrypoint"
fi

log "Serviços:"
docker stack services "$STACK_NAME" --format "  {{.Name}}\t{{.Replicas}}\t{{.Image}}" 2>/dev/null || true
echo ""
log "Logs:"
echo "  docker service logs -f ${STACK_NAME}_crm_backend"
echo "  docker service logs -f ${STACK_NAME}_crm_frontend"
echo "  docker service logs -f ${STACK_NAME}_crm_worker"
echo ""
