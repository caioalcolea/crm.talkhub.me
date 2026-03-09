#!/bin/bash
set -e

echo "============================================"
echo "  TalkHub CRM — Production Entrypoint"
echo "  SERVICE_ROLE: ${SERVICE_ROLE:-backend}"
echo "============================================"

# 1. Aguardar PostgreSQL
echo "[1/6] Waiting for PostgreSQL at ${DBHOST}:${DBPORT}..."
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
echo "[1/6] PostgreSQL is ready."

# Steps 2-6 only run for the backend (not worker/beat)
if [ "${SERVICE_ROLE}" = "worker" ] || [ "${SERVICE_ROLE}" = "beat" ]; then
    echo "Skipping migrations/static/admin for ${SERVICE_ROLE} role."
else
    # 2. Ensure application DB user exists (handles existing volumes where init script didn't run)
    echo "[2/6] Ensuring database user '${DBUSER}' exists..."
    python -c "
import os, psycopg2

# Connect as superuser (postgres) to manage roles
conn = psycopg2.connect(
    host=os.environ['DBHOST'],
    port=os.environ['DBPORT'],
    dbname=os.environ['DBNAME'],
    user='postgres',
    password=os.environ.get('POSTGRES_PASSWORD', os.environ.get('CRM_POSTGRES_PASSWORD', '16864b0c4a4e46c68d35ad644cca2791')),
)
conn.autocommit = True
cur = conn.cursor()

db_user = os.environ.get('DBUSER', 'crm_user')
db_pass = os.environ.get('DBPASSWORD', 'crm_talkhub_2026')

# Check if role exists
cur.execute(\"SELECT 1 FROM pg_roles WHERE rolname = %s\", (db_user,))
if cur.fetchone():
    # Role exists — update password to match current config
    cur.execute(f\"ALTER ROLE {db_user} WITH PASSWORD %s\", (db_pass,))
    print(f'  User {db_user} already exists — password updated.')
else:
    # Create the role
    cur.execute(f\"CREATE ROLE {db_user} WITH LOGIN PASSWORD %s\", (db_pass,))
    print(f'  User {db_user} created.')

# Grant privileges
cur.execute(f\"GRANT ALL PRIVILEGES ON DATABASE {os.environ['DBNAME']} TO {db_user}\")
cur.execute(f\"GRANT ALL ON SCHEMA public TO {db_user}\")

# Grant on existing tables/sequences (for existing DBs)
cur.execute(f\"GRANT ALL ON ALL TABLES IN SCHEMA public TO {db_user}\")
cur.execute(f\"GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO {db_user}\")

# Set default privileges for future objects
cur.execute(f\"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {db_user}\")
cur.execute(f\"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO {db_user}\")

cur.close()
conn.close()
print('  Database user setup complete.')
" 2>&1 || echo "  WARNING: Could not setup DB user via superuser (may already be configured)."

    # 3. Migrations
    echo "[3/6] Running migrations..."
    python manage.py migrate --noinput

    # 4. Verificar RLS status
    echo "[4/6] Checking Row-Level Security status..."
    python manage.py manage_rls --status 2>/dev/null || echo "  RLS check skipped (not PostgreSQL or command unavailable)."

    # 5. Static files
    echo "[5/6] Collecting static files..."
    python manage.py collectstatic --noinput

    # 6. Criar admin padrão
    echo "[6/6] Creating default admin user (if needed)..."
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
