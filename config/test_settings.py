"""Isolated configuration: python manage.py test --settings=config.test_settings.

Environment changes below affect only this test process. Never use this module
to serve the application: its public key and fast password hasher are test-only.
"""

import os

# Bootstrap shared settings without reading the developer's private .env or
# depending on credentials and debug flags supplied by the calling shell.
os.environ["DJANGO_LOAD_DOTENV"] = "false"
os.environ["DJANGO_SECRET_KEY"] = "ftms-synthetic-test-key-not-for-deployment"
os.environ["DJANGO_DEBUG"] = "false"
os.environ["DJANGO_ALLOWED_HOSTS"] = "testserver,localhost,127.0.0.1,[::1]"

from .settings import *  # noqa: F403,E402

SECRET_KEY = "ftms-synthetic-test-key-not-for-deployment"
DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1", "[::1]"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "TEST": {"NAME": ":memory:"},
    }
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
