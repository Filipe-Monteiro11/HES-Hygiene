from .settings import *
from decouple import config

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

IMAGEKIT_URL_ENDPOINT = config("IMAGEKIT_URL_ENDPOINT")
IMAGEKIT_PRIVATE_KEY = config("IMAGEKIT_PRIVATE_KEY")

STORAGES = {
    **STORAGES,
    "default": {
        "BACKEND": "produtos.storage.ImageKitStorage",
    },
}