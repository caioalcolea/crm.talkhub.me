-- ============================================================
-- TalkHub CRM — PostgreSQL RLS User Initialization
-- ============================================================
-- Cria o usuário de aplicação (NON-SUPERUSER) necessário para
-- que Row-Level Security funcione corretamente.
--
-- Este script roda automaticamente no primeiro boot do PostgreSQL
-- via /docker-entrypoint-initdb.d/
-- ============================================================

-- Criar usuário de aplicação (non-superuser é OBRIGATÓRIO para RLS)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'crm_user') THEN
        CREATE ROLE crm_user WITH LOGIN PASSWORD 'crm_talkhub_2026';
    END IF;
END
$$;

-- Conceder privilégios no database
GRANT ALL PRIVILEGES ON DATABASE crm_db TO crm_user;

-- Configurar schema public para o app user
\connect crm_db;
GRANT ALL ON SCHEMA public TO crm_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO crm_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO crm_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO crm_user;
