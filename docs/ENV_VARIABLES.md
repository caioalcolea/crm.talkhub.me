# Variáveis de Ambiente — TalkHub CRM

> Gerado automaticamente. Última atualização: 2026-03-04

## Legenda

| Coluna | Descrição |
|--------|-----------|
| Variável | Nome da variável de ambiente |
| Onde usada | Arquivo(s) que referenciam a variável |
| Padrão | Valor default no código |
| Obrigatória | Se a aplicação falha sem ela |
| No Docker Compose | Se está definida em `docker/djangocrm.yaml` |
| Status | ✅ OK, ⚠️ Faltando no deploy, 🗑️ Deprecated |

---

## Django Core

| Variável | Onde usada | Padrão | Obrigatória | No Compose | Status |
|----------|-----------|--------|-------------|------------|--------|
| `SECRET_KEY` | `settings.py` | `django-insecure-...` | ✅ Sim (prod) | ✅ | ✅ OK |
| `ENV_TYPE` | `settings.py` | `dev` | Não | ✅ (`prod`) | ✅ OK |
| `DEBUG` | `settings.py`, `server_settings.py` | `False` | Não | ✅ | ✅ OK |
| `ALLOWED_HOSTS` | `settings.py` | `localhost,127.0.0.1` | ✅ Sim (prod) | ✅ | ✅ OK |
| `DOMAIN_NAME` | `settings.py` | `http://localhost:8000` | Não | ✅ | ✅ OK |
| `FRONTEND_URL` | `settings.py` | `http://localhost:5173` | Não | ✅ | ✅ OK |
| `SWAGGER_ROOT_URL` | `settings.py` | `http://localhost:8000` | Não | ✅ | ✅ OK |
| `TIME_ZONE` | compose only | — | Não | ✅ | ✅ OK |

## Banco de Dados

| Variável | Onde usada | Padrão | Obrigatória | No Compose | Status |
|----------|-----------|--------|-------------|------------|--------|
| `DBNAME` | `settings.py` | `crm_db` | ✅ Sim | ✅ | ✅ OK |
| `DBUSER` | `settings.py` | `postgres` | ✅ Sim | ✅ (`crm_user`) | ✅ OK |
| `DBPASSWORD` | `settings.py` | `postgres` | ✅ Sim | ✅ | ✅ OK |
| `DBHOST` | `settings.py` | `localhost` | ✅ Sim | ✅ (`crm_db`) | ✅ OK |
| `DBPORT` | `settings.py` | `5432` | Não | ✅ | ✅ OK |

## Redis / Celery

| Variável | Onde usada | Padrão | Obrigatória | No Compose | Status |
|----------|-----------|--------|-------------|------------|--------|
| `CELERY_BROKER_URL` | `settings.py` | `redis://localhost:6379/0` | ✅ Sim | ✅ | ✅ OK |
| `CELERY_RESULT_BACKEND` | `settings.py` | `redis://localhost:6379/0` | ✅ Sim | ✅ | ✅ OK |

## MinIO S3 (Storage)

| Variável | Onde usada | Padrão | Obrigatória | No Compose | Status |
|----------|-----------|--------|-------------|------------|--------|
| `AWS_BUCKET_NAME` | `server_settings.py` | `talkhub-crm` | ✅ Sim (prod) | ✅ | ✅ OK |
| `AWS_ACCESS_KEY_ID` | `server_settings.py` | `""` | ✅ Sim (prod) | ✅ | ✅ OK |
| `AWS_SECRET_ACCESS_KEY` | `server_settings.py` | `""` | ✅ Sim (prod) | ✅ | ✅ OK |
| `AWS_S3_ENDPOINT_URL` | `server_settings.py` | `""` | ✅ Sim (MinIO) | ✅ | ✅ OK |
| `AWS_S3_CUSTOM_DOMAIN` | `server_settings.py` | `""` | Não | ❌ | ⚠️ Faltando (opcional) |

## Email (SMTP)

| Variável | Onde usada | Padrão | Obrigatória | No Compose | Status |
|----------|-----------|--------|-------------|------------|--------|
| `EMAIL_BACKEND` | `settings.py`, `server_settings.py` | `console` (dev) / `smtp` (prod) | Não | ✅ | ✅ OK |
| `EMAIL_HOST` | `settings.py`, `server_settings.py` | `smtp.titan.email` | ✅ Sim (prod) | ✅ | ✅ OK |
| `EMAIL_PORT` | `settings.py`, `server_settings.py` | `465` | Não | ✅ | ✅ OK |
| `EMAIL_USE_SSL` | `settings.py`, `server_settings.py` | `True` | Não | ✅ | ✅ OK |
| `EMAIL_USE_TLS` | `settings.py`, `server_settings.py` | `False` | Não | ❌ | ✅ OK (default) |
| `EMAIL_HOST_USER` | `settings.py`, `server_settings.py` | `""` | ✅ Sim (prod) | ✅ | ✅ OK |
| `EMAIL_HOST_PASSWORD` | `settings.py`, `server_settings.py` | `""` | ✅ Sim (prod) | ✅ | ✅ OK |
| `DEFAULT_FROM_EMAIL` | `settings.py` | `noreply@localhost` | ✅ Sim (prod) | ✅ | ✅ OK |
| `ADMIN_EMAIL` | `settings.py`, `create_default_admin.py` | `admin@localhost` | Não | ✅ | ✅ OK |
| `ADMIN_PASSWORD` | `create_default_admin.py` | `""` | ✅ Sim (setup) | ✅ | ✅ OK |

## Email (SES — não usado em produção)

| Variável | Onde usada | Padrão | Obrigatória | No Compose | Status |
|----------|-----------|--------|-------------|------------|--------|
| `AWS_SES_REGION_NAME` | `settings.py` | `ap-south-1` | Não (SES only) | ❌ | 🗑️ Não usado (SMTP ativo) |
| `AWS_SES_REGION_ENDPOINT` | `settings.py` | auto-gerado | Não (SES only) | ❌ | 🗑️ Não usado (SMTP ativo) |

## CORS / CSRF

| Variável | Onde usada | Padrão | Obrigatória | No Compose | Status |
|----------|-----------|--------|-------------|------------|--------|
| `CORS_ALLOWED_ORIGINS` | `settings.py` | `http://localhost:5173,...` | ✅ Sim (prod) | ✅ | ✅ OK |
| `CORS_ALLOW_ALL` | `settings.py` | `False` | Não | ✅ | ✅ OK |
| `CSRF_TRUSTED_ORIGINS` | `settings.py` | `""` | ✅ Sim (prod) | ✅ | ✅ OK |

## Google OAuth

| Variável | Onde usada | Padrão | Obrigatória | No Compose | Status |
|----------|-----------|--------|-------------|------------|--------|
| `GOOGLE_CLIENT_ID` | `settings.py` | `""` | Não (opcional) | ✅ | ✅ OK |
| `GOOGLE_CLIENT_SECRET` | `settings.py` | `""` | Não (opcional) | ✅ | ✅ OK |
| `GOOGLE_REDIRECT_URI` | `settings.py` | `""` | Não (opcional) | ❌ | ⚠️ Faltando (opcional) |

## Criptografia

| Variável | Onde usada | Padrão | Obrigatória | No Compose | Status |
|----------|-----------|--------|-------------|------------|--------|
| `FERNET_KEY` | `settings.py`, `integrations/views.py`, `channels/tasks.py`, `financeiro/` | `""` | ✅ Sim (prod) | ✅ | ✅ OK |

> **Nota**: Fernet key deve ser 32 bytes url-safe base64 (44 chars). No YAML, NÃO usar `${VAR:-default}` pois o `=` final é consumido pela interpolação Docker. Definir diretamente: `FERNET_KEY=chave_aqui`.

## Sentry

| Variável | Onde usada | Padrão | Obrigatória | No Compose | Status |
|----------|-----------|--------|-------------|------------|--------|
| `SENTRY_DSN` | `settings.py` | `""` | Não (opcional) | ✅ | ✅ OK |
| `SENTRY_ENVIRONMENT` | `settings.py` | `ENV_TYPE` | Não | ✅ | ✅ OK |
| `PUBLIC_SENTRY_DSN` | Frontend (`hooks.client.js`, `instrumentation.server.js`) | `""` | Não (opcional) | ✅ | ✅ OK |

## Frontend (SvelteKit)

| Variável | Onde usada | Padrão | Obrigatória | No Compose | Status |
|----------|-----------|--------|-------------|------------|--------|
| `PUBLIC_DJANGO_API_URL` | Frontend | — | ✅ Sim | ✅ | ✅ OK |
| `NODE_ENV` | Frontend | — | Não | ✅ | ✅ OK |
| `ORIGIN` | Frontend (SvelteKit CSRF) | — | ✅ Sim (prod) | ✅ | ✅ OK |

## Celery Worker/Beat

| Variável | Onde usada | Padrão | Obrigatória | No Compose | Status |
|----------|-----------|--------|-------------|------------|--------|
| `SERVICE_ROLE` | `entrypoint-prod.sh` | — | ✅ Sim | ✅ (`worker`/`beat`) | ✅ OK |

---

## Resumo

- **Total de variáveis no código**: 36
- **Presentes no Docker Compose**: 32
- **⚠️ Faltando no deploy**: 2 (GOOGLE_REDIRECT_URI, AWS_S3_CUSTOM_DOMAIN — ambos opcionais)
- **🗑️ Deprecated/não usadas**: 2 (AWS SES — SMTP ativo em produção)
- **Ação recomendada**: Remover referências SES se não houver plano de uso.
