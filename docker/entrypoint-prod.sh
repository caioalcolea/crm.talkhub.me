#!/bin/bash
set -e

echo "============================================"
echo "  TalkHub CRM — Production Entrypoint"
echo "  SERVICE_ROLE: ${SERVICE_ROLE:-backend}"
echo "============================================"

# 1. Aguardar PostgreSQL
echo "[1/5] Waiting for PostgreSQL at ${DBHOST}:${DBPORT}..."
retries=0
max_retries=30
while ! python -c "
import socket, os
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((os.environ['DBHOST'], int(os.environ['DBPORT'])))
s.close()
" 2>/dev/null; do
    retries=$((retries + 1))
    if [ "$retries" -ge "$max_retries" ]; then
        echo "ERROR: Could not connect to PostgreSQL after $max_retries attempts."
        exit 1
    fi
    echo "  PostgreSQL not ready yet (attempt $retries/$max_retries)..."
    sleep 1
done
echo "[1/5] PostgreSQL is ready."

# Steps 2-5 only run for the backend (not worker/beat)
if [ "${SERVICE_ROLE}" = "worker" ] || [ "${SERVICE_ROLE}" = "beat" ]; then
    echo "Skipping migrations/static/admin for ${SERVICE_ROLE} role."
else
    # 2. Migrations
    echo "[2/5] Running migrations..."
    python manage.py migrate --noinput

    # 3. Verificar RLS status
    echo "[3/5] Checking Row-Level Security status..."
    python manage.py manage_rls --status 2>/dev/null || echo "  RLS check skipped (not PostgreSQL or command unavailable)."

    # 4. Static files
    echo "[4/5] Collecting static files..."
    python manage.py collectstatic --noinput

    # 5. Criar admin padrão
    echo "[5/5] Creating default admin user (if needed)..."
    python manage.py create_default_admin
fi

# Determine what to run based on SERVICE_ROLE
case "${SERVICE_ROLE}" in
    worker)
        echo "============================================"
        echo "  Starting Celery Worker"
        echo "  Concurrency: ${CELERY_CONCURRENCY:-2}"
        echo "============================================"
        exec celery -A crm worker \
            --loglevel=info \
            --concurrency="${CELERY_CONCURRENCY:-2}"
        ;;
    beat)
        echo "============================================"
        echo "  Starting Celery Beat"
        echo "============================================"
        exec celery -A crm beat --loglevel=info
        ;;
    *)
        # If arguments were passed, run them instead of Gunicorn
        if [ $# -gt 0 ]; then
            echo "============================================"
            echo "  Running custom command: $@"
            echo "============================================"
            exec "$@"
        fi

        echo "============================================"
        echo "  Starting Gunicorn on 0.0.0.0:8000"
        echo "  Workers: ${GUNICORN_WORKERS:-3}"
        echo "============================================"
        exec gunicorn crm.wsgi:application \
            --workers "${GUNICORN_WORKERS:-3}" \
            --bind 0.0.0.0:8000 \
            --timeout 120 \
            --access-logfile - \
            --error-logfile -
        ;;
esac
