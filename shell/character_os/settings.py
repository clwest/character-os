"""
Django settings for character_os shell.

Phase 1 scaffold — minimal config that boots `python manage.py check`.
Database stays SQLite for the scaffold; Postgres+pgvector switches in
Phase 2 when the media data model migrates.

Secrets, allowed-hosts, and OAuth client ids land via django-environ
from a .env file once Phase 1 auth wiring begins.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING — placeholder for the scaffold only. Switch to
# env-driven before any real deployment.
SECRET_KEY = "django-insecure-scaffold-key-replace-before-deploy"  # noqa: S105

DEBUG = True

ALLOWED_HOSTS: list[str] = []


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "corsheaders",
    # Local apps — empty scaffold; models land in their own slices.
    "apps.accounts",
    "apps.spokespeople",
    "apps.videos",
    "apps.conversations",
    "apps.memory",
    "apps.billing",
    "apps.agents",
    "apps.embeddings",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "character_os.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "character_os.wsgi.application"
ASGI_APPLICATION = "character_os.asgi.application"


# Database — SQLite for scaffold. Postgres+pgvector in Phase 2.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# CORS — locked down by default. Phase 3 opens this to the SPA's origin.
CORS_ALLOWED_ORIGINS: list[str] = []


# DRF — minimal scaffold config.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
}


# Media-engine endpoint — the internal HTTP API for the FastAPI service.
# Defaults to localhost during dev; env-overridden in deployments.
MEDIA_ENGINE_BASE_URL = "http://localhost:8001"
