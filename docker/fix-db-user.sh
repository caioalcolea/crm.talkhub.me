#!/bin/bash
set -euo pipefail
# TalkHub CRM — Fix database user/password mismatch
# The crm_db volume has an existing PostgreSQL with unknown superuser password.
# This script tries common passwords, then creates/resets crm_user.

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
log()  { echo -e "${CYAN}[FIX]${NC} $*"; }
ok()   { echo -e "${GREEN}[FIX] OK${NC} $*"; }
fail() { echo -e "${RED}[FIX] FAIL${NC} $*"; exit 1; }

# Wait for crm_db to be ready
log "Waiting for crm_db to be ready..."
for i in $(seq 1 30); do
    if docker exec $(docker ps -q --filter name=djangocrm_crm_db) pg_isready -U postgres 2>/dev/null | grep -q "accepting"; then
        break
    fi
    [ "$i" -eq 30 ] && fail "crm_db not ready after 30s"
    sleep 1
done
ok "crm_db is ready"

DB_CONTAINER=$(docker ps -q --filter name=djangocrm_crm_db)
[ -z "$DB_CONTAINER" ] && fail "crm_db container not found. Is the stack deployed?"

CRM_USER="crm_user"
CRM_PASS="crm_talkhub_2026"

# Try common postgres superuser passwords
PASSWORDS=(
    "16864b0c4a4e46c68d35ad644cca2791"
    "postgres"
    ""
)

log "Trying to connect as postgres superuser..."
CONNECTED=false

# First try: use docker exec to bypass password authentication entirely
log "Attempting direct connection via docker exec (local socket)..."
if docker exec "$DB_CONTAINER" psql -U postgres -d crm_db -c "SELECT 1" &>/dev/null; then
    ok "Connected via docker exec (local socket)"
    CONNECTED=true

    log "Creating/resetting $CRM_USER..."
    docker exec "$DB_CONTAINER" psql -U postgres -d crm_db -c "
        DO \$\$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$CRM_USER') THEN
                CREATE ROLE $CRM_USER WITH LOGIN PASSWORD '$CRM_PASS';
                RAISE NOTICE 'Created user $CRM_USER';
            ELSE
                ALTER ROLE $CRM_USER WITH PASSWORD '$CRM_PASS';
                RAISE NOTICE 'Updated password for $CRM_USER';
            END IF;
        END
        \$\$;

        GRANT ALL PRIVILEGES ON DATABASE crm_db TO $CRM_USER;
    "
    ok "User $CRM_USER created/updated with password '$CRM_PASS'"

    log "Granting schema privileges..."
    docker exec "$DB_CONTAINER" psql -U postgres -d crm_db -c "
        GRANT ALL ON SCHEMA public TO $CRM_USER;
        GRANT ALL ON ALL TABLES IN SCHEMA public TO $CRM_USER;
        GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO $CRM_USER;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $CRM_USER;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $CRM_USER;
    "
    ok "Schema privileges granted"

    # Also reset postgres password to match our YAML default
    log "Updating postgres superuser password to match YAML default..."
    docker exec "$DB_CONTAINER" psql -U postgres -c "ALTER USER postgres WITH PASSWORD '16864b0c4a4e46c68d35ad644cca2791';"
    ok "Postgres superuser password updated"
fi

if ! $CONNECTED; then
    fail "Could not connect to PostgreSQL. Try: docker exec -it $DB_CONTAINER psql -U postgres"
fi

# Verify crm_user can connect
log "Verifying $CRM_USER can connect..."
if docker exec "$DB_CONTAINER" psql -U "$CRM_USER" -d crm_db -c "SELECT 1" &>/dev/null; then
    ok "$CRM_USER can connect successfully!"
else
    fail "$CRM_USER cannot connect. Check pg_hba.conf inside the container."
fi

echo ""
echo -e "${GREEN}Database fix complete!${NC}"
echo "Now force-restart the backend:"
echo "  docker service update --force djangocrm_crm_backend"
echo "  docker service update --force djangocrm_crm_frontend"
echo "  docker service update --force djangocrm_crm_worker"
echo "  docker service update --force djangocrm_crm_beat"
