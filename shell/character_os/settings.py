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

ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1", "testserver"]


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # django-allauth requirement
    "django.contrib.sites",
    # Third-party
    "rest_framework",
    "corsheaders",
    "allauth",
    "allauth.account",
    "allauth.headless",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
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

SITE_ID = 1

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # allauth account middleware — must come last; handles session
    # invalidation when sensitive account state changes.
    "allauth.account.middleware.AccountMiddleware",
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


# ---- Celery / Redis --------------------------------------------------
#
# Broker + result backend both ride on a single Redis instance
# (``infra/docker-compose.yml`` brings it up on :6379). Logical DB
# split keeps broker queues and result payloads in separate keyspaces
# so a ``FLUSHDB`` against one doesn't take out the other.
#
# All settings are env-overridable to keep production deploys driving
# off a managed Redis (e.g. ElastiCache) without code changes.
import os as _os  # noqa: E402 — keep imports terse at top of file

CELERY_BROKER_URL = _os.environ.get(
    "CELERY_BROKER_URL", "redis://localhost:6381/0",
)
CELERY_RESULT_BACKEND = _os.environ.get(
    "CELERY_RESULT_BACKEND", "redis://localhost:6381/1",
)
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
# Hard cap each task wall-clock at 15 min so a hung Runway poll can't
# pin a worker. Video generation should finish in <3 min in practice
# (mock mode is sub-second).
CELERY_TASK_TIME_LIMIT = 15 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 14 * 60
# Keep results around 24h for debugging; we don't read them in the
# happy path (state lives on the Video row), but eyeballing failures
# via celery-inspect is useful.
CELERY_RESULT_EXPIRES = 24 * 60 * 60


# ---- Authentication --------------------------------------------------

AUTHENTICATION_BACKENDS = [
    # Django's default — for the Django admin and email/password.
    "django.contrib.auth.backends.ModelBackend",
    # allauth — handles social auth (Google) + its own email-based flow.
    "allauth.account.auth_backends.AuthenticationBackend",
]

# allauth account config — design doc §6.4: email/password backup,
# Google OAuth primary. Magic links explicitly out.
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_EMAIL_VERIFICATION = "optional"  # tighten to "mandatory" pre-launch
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_PRESERVE_USERNAME_CASING = False

LOGIN_REDIRECT_URL = "/api/me/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# Google OAuth — credentials land via env in deploy; the provider is
# scaffolded here so the URL routes resolve but won't function until
# GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET are wired through the admin
# (SocialApp model) or via SOCIALACCOUNT_PROVIDERS["google"]["APP"].
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
        "OAUTH_PKCE_ENABLED": True,
    },
}
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_VERIFICATION = "none"
SOCIALACCOUNT_EMAIL_REQUIRED = True


# Dev convenience — email backend prints verification emails to console
# instead of sending them. Replace with SMTP/SES/Mailgun pre-launch.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "noreply@character-os.local"


# ---- allauth.headless ----------------------------------------------
#
# JSON-API surface for the Phase 3 SPA. The legacy HTML allauth flow
# stays alive (HEADLESS_ONLY=False) so the Django admin + the
# old-style /accounts/login/ pages keep working during the SPA
# transition. The headless surface mounts at /_allauth/ (router in
# urls.py) and splits by client type:
#
#   /_allauth/browser/v1/...   — session-cookie auth (this is the SPA)
#   /_allauth/app/v1/...       — token-based auth (mobile, deferred)
#
# We only enable the browser client today; the SPA will run as a
# first-party Vite/React app sharing the same origin (or a CORS-
# allowed origin) as Django, so session cookies are the natural fit.
#
# HEADLESS_FRONTEND_URLS tells allauth where to redirect users after
# email-verify / password-reset / account-confirm flows complete.
# These point at the SPA's eventual routes; until the SPA exists,
# they're 404s — that's fine, the headless API still works for the
# signup/login JSON calls.
HEADLESS_ONLY = False
HEADLESS_CLIENTS = ("browser",)
HEADLESS_FRONTEND_URLS = {
    # Tokens land in the URL query string; the SPA reads and forwards
    # to its own confirmation views.
    "account_confirm_email": "/account/verify-email/{key}",
    "account_reset_password": "/account/password/reset",
    "account_reset_password_from_key": "/account/password/reset/key/{key}",
    "account_signup": "/account/signup",
}
