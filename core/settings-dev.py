from core.settings import *  # noqa: F401, F403

SECRET_KEY = "django-insecure-dev-only-key-change-in-production"

DEBUG = True

ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

STATIC_ROOT = BASE_DIR / "staticfiles"  # noqa: F405

MEDIA_ROOT = BASE_DIR / "media"  # noqa: F405
