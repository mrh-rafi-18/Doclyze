"""
Doclyze Django Settings
Production-ready configuration with environment variable support.
"""

from pathlib import Path
from datetime import timedelta
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Security ──────────────────────────────────────────────────────────────────
SECRET_KEY: str = config("SECRET_KEY")
DEBUG: bool = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS: list[str] = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

# ── Applications ──────────────────────────────────────────────────────────────
INSTALLED_APPS: list[str] = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "corsheaders",
    "django_filters",
    # Local
    "apps.authentication.apps.AuthenticationConfig",
    "apps.users.apps.UsersConfig",
    "apps.documents.apps.DocumentsConfig",
]

MIDDLEWARE: list[str] = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF: str = "config.urls"
WSGI_APPLICATION: str = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ── Database ──────────────────────────────────────────────────────────────────
DATABASES: dict = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="doclyze"),
        "USER": config("DB_USER", default="postgres"),
        "PASSWORD": config("DB_PASSWORD", default=""),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
    }
}

# ── Auth ──────────────────────────────────────────────────────────────────────
AUTH_USER_MODEL: str = "users.User"

AUTH_PASSWORD_VALIDATORS: list[dict] = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ── REST Framework ────────────────────────────────────────────────────────────
REST_FRAMEWORK: dict = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardResultsPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "30/minute",
        "user": "120/minute",
        "auth": "10/minute",
    },
}

# ── JWT ───────────────────────────────────────────────────────────────────────
SIMPLE_JWT: dict = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=config("ACCESS_TOKEN_MINUTES", default=60, cast=int)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=config("REFRESH_TOKEN_DAYS", default=7, cast=int)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_OBTAIN_SERIALIZER": "apps.authentication.serializers.CustomTokenObtainPairSerializer",
}

# ── DRF Spectacular ───────────────────────────────────────────────────────────
SPECTACULAR_SETTINGS: dict = {
    "TITLE": "Doclyze API",
    "DESCRIPTION": "Document analysis API powered by PPStructureV3",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SORT_OPERATIONS": False,
}

# ── CORS ──────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS: list[str] = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000,http://127.0.0.1:3000",
    cast=Csv(),
)
CORS_ALLOW_CREDENTIALS: bool = True

# ── Email ─────────────────────────────────────────────────────────────────────
EMAIL_BACKEND: str = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST: str = config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT: int = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS: bool = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_HOST_USER: str = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD: str = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL: str = config("DEFAULT_FROM_EMAIL", default="noreply@doclyze.com")

# ── Storage / Media ───────────────────────────────────────────────────────────
MEDIA_ROOT: Path = BASE_DIR / "media"
MEDIA_URL: str = "/media/"

DOCUMENTS_UPLOAD_DIR: Path = MEDIA_ROOT / "documents" / "uploads"
DOCUMENTS_OUTPUT_DIR: Path = MEDIA_ROOT / "documents" / "outputs"
AVATARS_DIR: Path = MEDIA_ROOT / "avatars"

for _dir in (DOCUMENTS_UPLOAD_DIR, DOCUMENTS_OUTPUT_DIR, AVATARS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# ── Static ────────────────────────────────────────────────────────────────────
STATIC_URL: str = "/static/"
STATIC_ROOT: Path = BASE_DIR / "staticfiles"

# ── Celery ────────────────────────────────────────────────────────────────────
CELERY_BROKER_URL: str = config("REDIS_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND: str = config("REDIS_URL", default="redis://localhost:6379/0")
CELERY_TASK_SERIALIZER: str = "json"
CELERY_RESULT_SERIALIZER: str = "json"
CELERY_ACCEPT_CONTENT: list[str] = ["json"]
CELERY_TIMEZONE: str = "UTC"

# ── Cache ─────────────────────────────────────────────────────────────────────
CACHES: dict = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": config("REDIS_URL", default="redis://localhost:6379/1"),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}

# ── Internationalisation ──────────────────────────────────────────────────────
LANGUAGE_CODE: str = "en-us"
TIME_ZONE: str = "UTC"
USE_I18N: bool = True
USE_TZ: bool = True

DEFAULT_AUTO_FIELD: str = "django.db.models.BigAutoField"

# ── App-level constants ───────────────────────────────────────────────────────
FRONTEND_URL: str = config("FRONTEND_URL", default="http://localhost:3000")
MAX_UPLOAD_SIZE_MB: int = config("MAX_UPLOAD_SIZE_MB", default=50, cast=int)
ALLOWED_DOCUMENT_TYPES: list[str] = ["application/pdf", "image/jpeg", "image/png", "image/tiff"]
