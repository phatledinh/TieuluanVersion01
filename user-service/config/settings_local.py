"""
Local development settings override.
Uses SQLite for quick testing without Docker/MySQL.

Usage: set DJANGO_SETTINGS_MODULE=config.settings_local
"""

from .settings import *  # noqa: F401, F403

# Override database to SQLite for local dev
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

DEBUG = True
