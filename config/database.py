"""Database configuration shared by normal and PostgreSQL test settings."""

from django.core.exceptions import ImproperlyConfigured


def postgres_config(values):
    required = ("DJANGO_DB_NAME", "DJANGO_DB_USER", "DJANGO_DB_PASSWORD")
    for name in required:
        value = values.get(name)
        if not isinstance(value, str) or not value.strip():
            raise ImproperlyConfigured(f"{name} must be set for PostgreSQL.")
    port = values.get("DJANGO_DB_PORT", "5432")
    try:
        if not 1 <= int(port) <= 65535:
            raise ValueError
    except (ValueError, TypeError):
        raise ImproperlyConfigured("DJANGO_DB_PORT must be between 1 and 65535.") from None
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": values["DJANGO_DB_NAME"],
        "USER": values["DJANGO_DB_USER"],
        "PASSWORD": values["DJANGO_DB_PASSWORD"],
        "HOST": values.get("DJANGO_DB_HOST", "127.0.0.1"),
        "PORT": str(port),
        "OPTIONS": {"connect_timeout": 5},
    }


def database_config(values, base_dir):
    engine = values.get("DJANGO_DB_ENGINE", "sqlite").strip().lower()
    if engine == "postgresql":
        return postgres_config(values)
    if engine == "sqlite":
        return {"ENGINE": "django.db.backends.sqlite3", "NAME": base_dir / "db.sqlite3"}
    raise ImproperlyConfigured("DJANGO_DB_ENGINE must be sqlite or postgresql.")
