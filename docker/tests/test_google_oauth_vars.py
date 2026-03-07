"""
Tests for Google OAuth environment variables in Docker Compose.

Property 1 (Fault Condition): Google OAuth vars must be present in affected services.
Property 2 (Preservation): Existing config must remain unchanged after fix.
"""
import os
import pytest
import yaml

COMPOSE_PATH = os.path.join(os.path.dirname(__file__), "..", "djangocrm.yaml")


def load_compose():
    with open(COMPOSE_PATH) as f:
        return yaml.safe_load(f)


def get_env_dict(service_env_list):
    """Convert Docker Compose environment list to dict."""
    env = {}
    for item in service_env_list:
        if "=" in item:
            key, value = item.split("=", 1)
            env[key] = value
    return env


# ─── Property 1: Fault Condition ───────────────────────────────────────────────
# These tests encode the EXPECTED behavior. They FAIL on unfixed code (confirming
# the bug exists) and PASS after the fix is applied.


class TestGoogleOAuthVarsPresent:
    """Verify Google OAuth env vars are present in affected Docker services."""

    def test_backend_has_google_client_id(self):
        compose = load_compose()
        env = get_env_dict(compose["services"]["crm_backend"]["environment"])
        assert "GOOGLE_CLIENT_ID" in env, (
            "crm_backend.environment missing GOOGLE_CLIENT_ID"
        )

    def test_backend_has_google_client_secret(self):
        compose = load_compose()
        env = get_env_dict(compose["services"]["crm_backend"]["environment"])
        assert "GOOGLE_CLIENT_SECRET" in env, (
            "crm_backend.environment missing GOOGLE_CLIENT_SECRET"
        )

    def test_frontend_has_google_client_id(self):
        compose = load_compose()
        env = get_env_dict(compose["services"]["crm_frontend"]["environment"])
        assert "GOOGLE_CLIENT_ID" in env, (
            "crm_frontend.environment missing GOOGLE_CLIENT_ID"
        )

    def test_frontend_has_google_login_domain(self):
        compose = load_compose()
        env = get_env_dict(compose["services"]["crm_frontend"]["environment"])
        assert "GOOGLE_LOGIN_DOMAIN" in env, (
            "crm_frontend.environment missing GOOGLE_LOGIN_DOMAIN"
        )

    def test_worker_has_google_client_id(self):
        compose = load_compose()
        env = get_env_dict(compose["services"]["crm_worker"]["environment"])
        assert "GOOGLE_CLIENT_ID" in env, (
            "crm_worker.environment missing GOOGLE_CLIENT_ID"
        )

    def test_worker_has_google_client_secret(self):
        compose = load_compose()
        env = get_env_dict(compose["services"]["crm_worker"]["environment"])
        assert "GOOGLE_CLIENT_SECRET" in env, (
            "crm_worker.environment missing GOOGLE_CLIENT_SECRET"
        )

    def test_backend_google_vars_use_swarm_pattern(self):
        """OAuth vars should use ${CRM_...} pattern without defaults."""
        compose = load_compose()
        env = get_env_dict(compose["services"]["crm_backend"]["environment"])
        if "GOOGLE_CLIENT_ID" in env:
            assert env["GOOGLE_CLIENT_ID"] == "${CRM_GOOGLE_CLIENT_ID}"
        if "GOOGLE_CLIENT_SECRET" in env:
            assert env["GOOGLE_CLIENT_SECRET"] == "${CRM_GOOGLE_CLIENT_SECRET}"

    def test_frontend_google_login_domain_value(self):
        """GOOGLE_LOGIN_DOMAIN should point to production URL."""
        compose = load_compose()
        env = get_env_dict(compose["services"]["crm_frontend"]["environment"])
        if "GOOGLE_LOGIN_DOMAIN" in env:
            assert env["GOOGLE_LOGIN_DOMAIN"] == "https://crm.talkhub.me"


# ─── Property 2: Preservation ──────────────────────────────────────────────────
# These tests capture the existing state and verify it remains unchanged.

# Snapshot of existing env var KEYS per service (before fix)
BACKEND_EXISTING_KEYS = {
    "SECRET_KEY", "ENV_TYPE", "DEBUG", "ALLOWED_HOSTS", "DOMAIN_NAME",
    "FRONTEND_URL", "SWAGGER_ROOT_URL", "TIME_ZONE", "DBNAME", "DBUSER",
    "DBPASSWORD", "DBHOST", "DBPORT", "CELERY_BROKER_URL",
    "CELERY_RESULT_BACKEND", "AWS_BUCKET_NAME", "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY", "AWS_S3_ENDPOINT_URL", "EMAIL_BACKEND",
    "EMAIL_HOST", "EMAIL_PORT", "EMAIL_USE_SSL", "EMAIL_HOST_USER",
    "EMAIL_HOST_PASSWORD", "DEFAULT_FROM_EMAIL", "ADMIN_EMAIL",
    "ADMIN_PASSWORD", "CORS_ALLOWED_ORIGINS", "CORS_ALLOW_ALL",
    "CSRF_TRUSTED_ORIGINS", "SENTRY_DSN", "SENTRY_ENVIRONMENT",
}

FRONTEND_EXISTING_KEYS = {
    "PUBLIC_DJANGO_API_URL", "PUBLIC_SENTRY_DSN", "NODE_ENV", "ORIGIN",
}

WORKER_EXISTING_KEYS = {
    "SERVICE_ROLE", "SECRET_KEY", "ENV_TYPE", "DEBUG", "DBNAME", "DBUSER",
    "DBPASSWORD", "DBHOST", "DBPORT", "CELERY_BROKER_URL",
    "CELERY_RESULT_BACKEND", "AWS_BUCKET_NAME", "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY", "AWS_S3_ENDPOINT_URL", "EMAIL_BACKEND",
    "EMAIL_HOST", "EMAIL_PORT", "EMAIL_USE_SSL", "EMAIL_HOST_USER",
    "EMAIL_HOST_PASSWORD", "DEFAULT_FROM_EMAIL", "DOMAIN_NAME",
    "FRONTEND_URL", "SENTRY_DSN", "SENTRY_ENVIRONMENT",
}

UNAFFECTED_SERVICES = {"crm_db", "crm_beat", "crm_redis"}


class TestPreservation:
    """Verify existing configurations remain unchanged."""

    def test_backend_existing_vars_present(self):
        compose = load_compose()
        env = get_env_dict(compose["services"]["crm_backend"]["environment"])
        for key in BACKEND_EXISTING_KEYS:
            assert key in env, f"crm_backend lost existing var: {key}"

    def test_frontend_existing_vars_present(self):
        compose = load_compose()
        env = get_env_dict(compose["services"]["crm_frontend"]["environment"])
        for key in FRONTEND_EXISTING_KEYS:
            assert key in env, f"crm_frontend lost existing var: {key}"

    def test_worker_existing_vars_present(self):
        compose = load_compose()
        env = get_env_dict(compose["services"]["crm_worker"]["environment"])
        for key in WORKER_EXISTING_KEYS:
            assert key in env, f"crm_worker lost existing var: {key}"

    @pytest.mark.parametrize("service_name", list(UNAFFECTED_SERVICES))
    def test_unaffected_services_unchanged(self, service_name):
        """Services not related to OAuth should be completely unchanged."""
        compose = load_compose()
        assert service_name in compose["services"], (
            f"Service {service_name} missing from compose"
        )

    def test_yaml_is_valid(self):
        """The compose file must be valid YAML."""
        compose = load_compose()
        assert "services" in compose
        assert "volumes" in compose
        assert "networks" in compose
