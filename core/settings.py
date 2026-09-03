import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY")

DEBUG = os.getenv("DEBUG", "0") == "1"

ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "jazzmin",
    "modeltranslation",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "mptt",
    "apps.accounts",
    "apps.addresses",
    "apps.categories",
    "apps.figures",
    "apps.website",
    "apps.carts",
    "apps.orders",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.global_context",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB"),
        "USER": os.getenv("POSTGRES_USER"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        "HOST": os.getenv("POSTGRES_HOST", "db"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}

AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "website:home"
LOGOUT_REDIRECT_URL = "website:home"

DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL", "Magno Figures <no-reply@example.com>"
)

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "1") == "1"
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "0") == "1"
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "15"))

SERVER_EMAIL = os.getenv("SERVER_EMAIL", DEFAULT_FROM_EMAIL)

DOMAIN = os.getenv("DOMAIN") or "localhost:8000"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"

LANGUAGES = [
    ("pt-br", "Português"),
]

DATA_UPLOAD_MAX_NUMBER_FILES = 50

FIGURES_PER_PAGE = 12

MODELTRANSLATION_DEFAULT_LANGUAGE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://redis:6379/0"),
    }
}

CSRF_TRUSTED_ORIGINS = [
    f"https://{host}" for host in ALLOWED_HOSTS if host != "*"
]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SUPERFRETE_TOKEN = os.getenv("SUPERFRETE_TOKEN", "")
SUPERFRETE_SANDBOX = os.getenv("SUPERFRETE_SANDBOX", "0") == "1"
SUPERFRETE_USER_AGENT_EMAIL = os.getenv(
    "SUPERFRETE_USER_AGENT_EMAIL"
) or "example@example.com"
SUPERFRETE_SERVICES = os.getenv("SUPERFRETE_SERVICES", "1,2")

JAZZMIN_SETTINGS = {
    "site_title": "Magno Figures",
    "site_header": "Magno Figures",
    "site_brand": "Magno Figures",
    "welcome_sign": "Bem-vindo ao painel administrativo",
    "copyright": "VWTech Dev",
    "search_model": ["accounts.User", "figures.Figure"],
    "show_sidebar": True,
    "navigation_expanded": True,
    "order_with_respect_to": [
        "apps.accounts",
        "apps.figures",
        "apps.categories",
        "apps.orders",
        "apps.carts",
        "apps.addresses",
        "apps.website",
    ],
    "icons": {
        "accounts.User": "fas fa-users",
        "figures.Figure": "fas fa-user-astronaut",
        "figures.FigureImage": "fas fa-images",
        "categories.Category": "fas fa-tags",
        "orders.Order": "fas fa-shopping-cart",
        "orders.OrderItem": "fas fa-box",
        "carts.Cart": "fas fa-shopping-basket",
        "carts.CartItem": "fas fa-cart-plus",
        "addresses.Address": "fas fa-map-marker-alt",
        "website.Website": "fas fa-cog",
    },
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-dark",
    "accent": "accent-primary",
    "navbar": "navbar-dark navbar-black",
    "no_navbar_border": False,
    "navbar_fixed": False,
    "layout_options": {
        "dark_mode_toggle": True
    },
    "dark_mode_theme": "darkly",
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    }
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{levelname}] {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "file": {
            "level": "WARNING",
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "logs" / "django.log",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["file"],
        "level": "WARNING",
    },
}
