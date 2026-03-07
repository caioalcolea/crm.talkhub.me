#!/bin/bash

# Script de deploy do TalkHub MCP Server
# Uso: ./deploy.sh [build|deploy|update|logs|stop|restart|status]

set -e

STACK_NAME="mcp"
IMAGE_NAME="talkhub/mcp-server:latest"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
echo_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }

build_image() {
    echo_info "Construindo imagem Docker..."
    docker build -t $IMAGE_NAME .
    echo_info "Imagem construída com sucesso!"
}

deploy_stack() {
    echo_info "Fazendo deploy do stack $STACK_NAME..."
    docker stack deploy -c docker-compose.yml $STACK_NAME
    echo_info "Stack deployado com sucesso!"
    echo_info "Aguardando serviços iniciarem..."
    sleep 10
    docker stack ps $STACK_NAME
}

clean_deploy() {
    echo_warn "Removendo stack $STACK_NAME..."
    docker stack rm $STACK_NAME 2>/dev/null || true
    echo_info "Aguardando containers pararem..."
    sleep 10

    echo_info "Limpando imagens e containers antigos..."
    docker container prune -f
    docker image prune -f
    sleep 3

    echo_info "Removendo imagem antiga..."
    docker rmi $IMAGE_NAME 2>/dev/null || true

    build_image
    echo_info "Aguardando 5s antes do deploy..."
    sleep 5
    deploy_stack
}

update_service() {
    echo_info "Atualizando serviço..."
    build_image
    docker service update --image $IMAGE_NAME ${STACK_NAME}_mcp_server --force
    echo_info "Serviço atualizado com sucesso!"
}

show_logs() {
    docker service logs -f ${STACK_NAME}_mcp_server
}

stop_stack() {
    echo_warn "Parando stack $STACK_NAME..."
    docker stack rm $STACK_NAME
    echo_info "Stack removido!"
}

restart_stack() {
    clean_deploy
}

show_status() {
    echo_info "Status do stack $STACK_NAME:"
    docker stack ps $STACK_NAME
    echo ""
    echo_info "Serviços:"
    docker stack services $STACK_NAME
}

case "${1:-deploy}" in
    build)   build_image ;;
    deploy)  clean_deploy ;;
    update)  update_service ;;
    logs)    show_logs ;;
    stop)    stop_stack ;;
    restart) clean_deploy ;;
    status)  show_status ;;
    *)
        echo "Uso: $0 {build|deploy|update|logs|stop|restart|status}"
        exit 1
        ;;
esac
