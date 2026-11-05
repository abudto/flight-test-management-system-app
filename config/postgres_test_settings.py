"""PostgreSQL tests with synthetic application settings and a separate role.

Local runs read only database credentials from .env. CI supplies these variables
directly and disables that read with DJANGO_TEST_LOAD_DOTENV=false.
The development database/user/password are deliberately not used here.
"""

import os

from dotenv import dotenv_values

from .test_settings import *  # noqa: F403
from .database import postgres_config

local_values = dotenv_values(BASE_DIR / ".env") if env_bool(  # noqa: F405
    "DJANGO_TEST_LOAD_DOTENV", default=True,
) else {}


def test_value(name, default=""):
    return os.environ.get(name, local_values.get(name, default))


test_name = test_value("DJANGO_TEST_DB_NAME", "test_ftms")
development_name = test_value("DJANGO_DB_NAME", "ftms_dev")
if not test_name.startswith("test_") or test_name in {development_name, "postgres", "template0", "template1"}:
    raise ImproperlyConfigured(  # noqa: F405
        "DJANGO_TEST_DB_NAME must start with test_ and differ from the development database.",
    )

DATABASES = {"default": postgres_config({
    # Django's maintenance connection creates/destroys only TEST.NAME.
    "DJANGO_DB_NAME": "postgres",
    "DJANGO_DB_USER": test_value("DJANGO_TEST_DB_USER"),
    "DJANGO_DB_PASSWORD": test_value("DJANGO_TEST_DB_PASSWORD"),
    "DJANGO_DB_HOST": test_value("DJANGO_TEST_DB_HOST", "127.0.0.1"),
    "DJANGO_DB_PORT": test_value("DJANGO_TEST_DB_PORT", "5432"),
})}
DATABASES["default"]["TEST"] = {"NAME": test_name}
