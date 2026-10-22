
"""
Configurações do HES Atacado.
Django + Neon PostgreSQL + ImageKit.
"""

from pathlib import Path

from decouple import config


BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"


# SEGURANÇA
SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = [
    host.strip()
    for host in config(
        "ALLOWED_HOSTS",
        default="localhost,127.0.0.1",
    ).split(",")
    if host.strip()
]

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in config(
        "CSRF_TRUSTED_ORIGINS",
        default="",
    ).split(",")
    if origin.strip()
]


# APLICAÇÕES
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "storages",
    "produtos",
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# MIDDLEWARE
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "config.middleware.AdminSessionOnlyMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"


# TEMPLATES
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [FRONTEND_DIR / "html"],
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

WSGI_APPLICATION = "config.wsgi.application"


# NEON POSTGRESQL
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("NEON_DB_NAME"),
        "USER": config("NEON_DB_USER"),
        "PASSWORD": config("NEON_DB_PASSWORD"),
        "HOST": config("NEON_DB_HOST"),
        "PORT": config("NEON_DB_PORT", default="5432"),
        "OPTIONS": {
            "sslmode": "require",
            "connect_timeout": 10,
        },
        "CONN_MAX_AGE": 0,
        "CONN_HEALTH_CHECKS": True,
    }
}


# AUTENTICAÇÃO
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# IDIOMA E FUSO HORÁRIO
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True


# ARQUIVOS ESTÁTICOS
STATIC_URL = "/static/"

STATICFILES_DIRS = (
    [FRONTEND_DIR] if FRONTEND_DIR.exists() else []
)

STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = BASE_DIR / "media"

WHITENOISE_COMPRESS = True
WHITENOISE_MAX_AGE = 31536000


# IMAGEKIT
IMAGEKIT_URL_ENDPOINT = config(
    "IMAGEKIT_URL_ENDPOINT"
).rstrip("/")

IMAGEKIT_PRIVATE_KEY = config("IMAGEKIT_PRIVATE_KEY")

MEDIA_URL = f"{IMAGEKIT_URL_ENDPOINT}/"

STORAGES = {
    "default": {
        "BACKEND": "produtos.storage.ImageKitStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}


# EMAIL
EMAIL_BACKEND = (
    "django.core.mail.backends.console.EmailBackend"
)


# CACHE
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "cache-hes",
    }
}


# SESSÕES
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_AGE = 60 * 60 * 8
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_HTTPONLY = True


# SEGURANÇA DE PRODUÇÃO
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = (
        "HTTP_X_FORWARDED_PROTO",
        "https",
    )

    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True