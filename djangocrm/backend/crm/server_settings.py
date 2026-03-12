"""
TalkHub Production Settings Override
=====================================
Sobrescreve server_settings.py do Django-CRM para usar:
- MinIO S3 (em vez de AWS S3)
- SMTP Titan (em vez de AWS SES)
- Sentry opcional
"""

import os

DEBUG = False

# ============================
# MinIO S3 Storage
# ============================
AWS_STORAGE_BUCKET_NAME = AWS_BUCKET_NAME = os.environ.get("AWS_BUCKET_NAME", "talkhub-crm")
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")

# MinIO endpoint (diferente do AWS padrão)
AWS_S3_ENDPOINT_URL = os.environ.get("AWS_S3_ENDPOINT_URL", "")

# Para MinIO, NÃO usar custom domain (diferente do AWS S3)
AWS_S3_CUSTOM_DOMAIN = os.environ.get("AWS_S3_CUSTOM_DOMAIN", "")
if not AWS_S3_CUSTOM_DOMAIN:
    AWS_S3_CUSTOM_DOMAIN = None

AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=86400",
}

# Django 5.x STORAGES override for media files (replaces deprecated DEFAULT_FILE_STORAGE)
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
    },
}
DEFAULT_S3_PATH = "media"

MEDIA_ROOT = f"/{DEFAULT_S3_PATH}/"

# Para MinIO com endpoint personalizado
if AWS_S3_ENDPOINT_URL:
    MEDIA_URL = f"{AWS_S3_ENDPOINT_URL}/{AWS_BUCKET_NAME}/{DEFAULT_S3_PATH}/"
else:
    S3_DOMAIN = str(AWS_BUCKET_NAME) + ".s3.amazonaws.com"
    MEDIA_URL = f"//{S3_DOMAIN}/{DEFAULT_S3_PATH}/"

# CORS configurado via env vars em settings.py principal
# NÃO sobrescrever aqui para evitar CORS_ORIGIN_ALLOW_ALL = True em produção

AWS_IS_GZIPPED = True
AWS_ENABLED = True
AWS_S3_SECURE_URLS = True
AWS_S3_FILE_OVERWRITE = False

# MinIO-specific: forçar path-style (em vez de virtual-hosted-style)
AWS_S3_ADDRESSING_STYLE = "path"

# Email is configured in settings.py via env vars (EMAIL_BACKEND, EMAIL_HOST, etc.)
# Do NOT redefine here — the star-import would override settings.py values.

# ============================
# Segurança (cookies)
# ============================
SESSION_COOKIE_DOMAIN = ".talkhub.me"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# ============================
# Sentry (melhorado — CeleryIntegration + DjangoIntegration com transaction_style)
# ============================
# Sentry é inicializado no settings.py principal (final do arquivo)
# para funcionar em todos os ambientes quando SENTRY_DSN estiver presente.
