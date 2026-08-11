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

EMAIL_BACKEND = "core.mail.EmailBackend"

STATIC_ROOT = BASE_DIR / "staticfiles"  # noqa: F405

MEDIA_ROOT = BASE_DIR / "media"  # noqa: F405

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
