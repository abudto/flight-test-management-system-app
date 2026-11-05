"""Database settings validation does not connect to or modify any database."""

import os
from pathlib import Path
import subprocess
import sys

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from .database import database_config, postgres_config


class DatabaseConfigurationTests(SimpleTestCase):
    def values(self, **overrides):
        values = {"DJANGO_DB_ENGINE": "postgresql", "DJANGO_DB_NAME": "synthetic_dev",
                  "DJANGO_DB_USER": "synthetic_app", "DJANGO_DB_PASSWORD": "synthetic-password"}
        values.update(overrides)
        return values

    def test_sqlite_remains_available_without_postgres_credentials(self):
        self.assertEqual(database_config({}, Path("/synthetic")), {
            "ENGINE": "django.db.backends.sqlite3", "NAME": Path("/synthetic/db.sqlite3"),
        })

    def test_postgres_configuration_preserves_credentials_and_connection_values(self):
        config = database_config(self.values(DJANGO_DB_HOST="db.example.invalid",
                                            DJANGO_DB_PORT="5433"), Path("/synthetic"))
        self.assertEqual(config["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(config["NAME"], "synthetic_dev")
        self.assertEqual(config["USER"], "synthetic_app")
        self.assertEqual(config["PASSWORD"], "synthetic-password")
        self.assertEqual(config["HOST"], "db.example.invalid")
        self.assertEqual(config["PORT"], "5433")

    def test_postgres_connection_defaults_are_local(self):
        config = postgres_config(self.values())
        self.assertEqual(config["HOST"], "127.0.0.1")
        self.assertEqual(config["PORT"], "5432")

    def test_required_postgres_values_fail_explicitly_without_exposing_password(self):
        for name in ["DJANGO_DB_NAME", "DJANGO_DB_USER", "DJANGO_DB_PASSWORD"]:
            for value in ["", "   ", None]:
                with self.subTest(name=name, value=value):
                    with self.assertRaises(ImproperlyConfigured) as error:
                        postgres_config(self.values(**{name: value}))
                    self.assertIn(name, str(error.exception))
                    self.assertNotIn("synthetic-password", str(error.exception))

    def test_invalid_port_fails_explicitly(self):
        for port in ["abc", "0", "65536", "", None]:
            with self.subTest(port=port):
                with self.assertRaisesMessage(ImproperlyConfigured, "DJANGO_DB_PORT"):
                    postgres_config(self.values(DJANGO_DB_PORT=port))

    def test_unknown_backend_does_not_silently_fall_back(self):
        with self.assertRaisesMessage(ImproperlyConfigured, "DJANGO_DB_ENGINE"):
            database_config({"DJANGO_DB_ENGINE": "postgreql"}, Path("/synthetic"))

    def run_settings(self, source, **extra):
        env = {key: value for key, value in os.environ.items() if not key.startswith("DJANGO_")}
        env.update(DJANGO_TEST_LOAD_DOTENV="false", DJANGO_TEST_DB_USER="synthetic_test",
                   DJANGO_TEST_DB_PASSWORD="synthetic-test-password", DJANGO_TEST_DB_NAME="test_synthetic")
        env.update(extra)
        return subprocess.run([sys.executable, "-B", "-c", source], env=env,
                              capture_output=True, text=True)

    def test_postgres_tests_use_separate_role_and_explicit_database_name(self):
        result = self.run_settings(
            "import config.postgres_test_settings as s; d=s.DATABASES['default']; "
            "assert d['ENGINE']=='django.db.backends.postgresql'; "
            "assert d['USER']=='synthetic_test'; assert d['TEST']['NAME']=='test_synthetic'; "
            "assert d['NAME']=='postgres'; assert s.DEBUG is False",
            DJANGO_DB_NAME="synthetic_dev", DJANGO_DB_USER="synthetic_app",
            DJANGO_DB_PASSWORD="synthetic-development-password",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_postgres_test_name_cannot_target_development_or_system_database(self):
        for name in ["synthetic_dev", "postgres", "template0", "test_same"]:
            with self.subTest(name=name):
                result = self.run_settings("import config.postgres_test_settings",
                                           DJANGO_TEST_DB_NAME=name, DJANGO_DB_NAME="test_same")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("DJANGO_TEST_DB_NAME", result.stderr)

    def test_postgres_tests_require_test_credentials_instead_of_using_development_role(self):
        result = self.run_settings("import config.postgres_test_settings",
                                   DJANGO_TEST_DB_USER="", DJANGO_DB_USER="synthetic_app")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DJANGO_DB_USER", result.stderr)

    def test_sqlite_test_settings_ignore_development_database_environment(self):
        result = self.run_settings(
            "import config.test_settings as s; assert s.DATABASES['default']['NAME']==':memory:'",
            DJANGO_DB_ENGINE="postgresql", DJANGO_DB_NAME="synthetic_dev",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
