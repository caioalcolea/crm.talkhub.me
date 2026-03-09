#!/bin/bash
set -e

echo "============================================"
echo "  TalkHub CRM — Production Entrypoint"
echo "  SERVICE_ROLE: ${SERVICE_ROLE:-backend}"
echo "============================================"

# 1. Aguardar PostgreSQL (safe defaults for missing env vars)
DB_HOST="${DBHOST:-crm_db}"
DB_PORT="${DBPORT:-5432}"
echo "[1/6] Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}..."
retries=0
max_retries=30
while ! python -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(3)
s.connect(('${DB_HOST}', ${DB_PORT}))
s.close()
" 2>/dev/null; do
    retries=$((retries + 1))
    if [ "$retries" -ge "$max_retries" ]; then
        echo "ERROR: Could not connect to PostgreSQL after $max_retries attempts."
        exit 1
    fi
    echo "  PostgreSQL not ready yet (attempt $retries/$max_retries)..."
    sleep 2
done
echo "[1/6] PostgreSQL is ready."

# Steps 2-6 only run for the backend (not worker/beat)
if [ "${SERVICE_ROLE}" = "worker" ] || [ "${SERVICE_ROLE}" = "beat" ]; then
    echo "Skipping migrations/static/admin for ${SERVICE_ROLE} role."
else
    # 2. Ensure application DB user exists
    #    Strategy: try app user first, only use superuser as fallback
    echo "[2/6] Ensuring database user '${DBUSER:-crm_user}' can connect..."
    python -c "
import os, sys, psycopg2

db_host = os.environ.get('DBHOST', 'crm_db')
db_port = os.environ.get('DBPORT', '5432')
db_name = os.environ.get('DBNAME', 'crm_db')
db_user = os.environ.get('DBUSER', 'crm_user')
db_pass = os.environ.get('DBPASSWORD', 'crm_talkhub_2026')

# Try connecting as the app user directly
try:
    conn = psycopg2.connect(host=db_host, port=db_port, dbname=db_name, user=db_user, password=db_pass)
    conn.close()
    print(f'  User {db_user} can connect — OK.')
    sys.exit(0)
except psycopg2.OperationalError:
    print(f'  User {db_user} cannot connect — attempting superuser setup...')

# Fallback: superuser to create/fix the app user
pg_pass = os.environ.get('POSTGRES_PASSWORD', '16864b0c4a4e46c68d35ad644cca2791')
try:
    conn = psycopg2.connect(host=db_host, port=db_port, dbname=db_name, user='postgres', password=pg_pass)
except psycopg2.OperationalError as e:
    print(f'  WARNING: Cannot connect as superuser: {e}')
    print(f'  Proceeding — migrations may fail if {db_user} does not exist.')
    sys.exit(0)

conn.autocommit = True
cur = conn.cursor()

cur.execute('SELECT 1 FROM pg_roles WHERE rolname = %s', (db_user,))
if cur.fetchone():
    cur.execute(f'ALTER ROLE {db_user} WITH PASSWORD %s', (db_pass,))
    print(f'  User {db_user} password updated.')
else:
    cur.execute(f'CREATE ROLE {db_user} WITH LOGIN PASSWORD %s', (db_pass,))
    print(f'  User {db_user} created.')

cur.execute(f'GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user}')
cur.execute(f'GRANT ALL ON SCHEMA public TO {db_user}')
cur.execute(f'GRANT ALL ON ALL TABLES IN SCHEMA public TO {db_user}')
cur.execute(f'GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO {db_user}')
cur.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {db_user}')
cur.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO {db_user}')

cur.close()
conn.close()
print('  Database user setup complete.')
" 2>&1 || echo "  WARNING: DB user setup failed (may already be configured)."

    # 3. Migrations
    echo "[3/6] Running migrations..."
    python manage.py migrate --noinput

    # 4. Verificar RLS status
    echo "[4/6] Checking Row-Level Security status..."
    python manage.py manage_rls --status 2>/dev/null || echo "  RLS check skipped."

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
        if [ $# -gt 0 ]; then
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
