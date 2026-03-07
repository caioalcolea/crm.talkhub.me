-- ============================================================
-- TalkHub CRM — PostgreSQL RLS User Initialization
-- ============================================================
-- Creates the application user (NON-SUPERUSER) required for
-- Row-Level Security to work correctly.
--
-- This script runs automatically on first PostgreSQL boot
-- via /docker-entrypoint-initdb.d/
--
-- The password is read from the CRM_DB_PASSWORD environment
-- variable (passed to the postgres container).
-- ============================================================

-- Create application user (non-superuser is REQUIRED for RLS)
DO $$
DECLARE
    db_password TEXT := current_setting('crm.db_password', true);
BEGIN
    IF db_password IS NULL OR db_password = '' THEN
        db_password := 'crm_talkhub_2026';
        RAISE WARNING 'CRM_DB_PASSWORD not set, using default (NOT recommended for production)';
    END IF;

    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'crm_user') THEN
        EXECUTE format('CREATE ROLE crm_user WITH LOGIN PASSWORD %L', db_password);
    ELSE
        EXECUTE format('ALTER ROLE crm_user WITH PASSWORD %L', db_password);
    END IF;
END
$$;

-- Grant privileges on database
GRANT ALL PRIVILEGES ON DATABASE crm_db TO crm_user;

-- Configure public schema for the app user
\connect crm_db;
GRANT ALL ON SCHEMA public TO crm_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO crm_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO crm_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO crm_user;
