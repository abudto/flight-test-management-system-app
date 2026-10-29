# Flight Test Management System (FTMS)

FTMS is a Django engineering portfolio project for aircraft flight-test planning.
It brings programs, engineering test specifications, test points, cards, and
sequences into a relational application with reusable document exports.

Flight-test planning requires consistent conditions, procedures, identifiers, and
relationships. This project applies Python and web development to that problem,
with an emphasis on data integrity and a foundation for engineering traceability.
It is currently a planning prototype; it does not establish regulatory compliance
or provide approved operational instructions.

## Current functionality

| Capability | Current implementation |
|---|---|
| Programs and aircraft | Records managed through Django admin |
| Engineering planning | Engineering requirements, tests, points, and conditions |
| Test matrix | Program-specific HTML table and Excel download |
| Test cards | Admin authoring and PDF export |
| Test sequences | Ordered points, optional cards, dates, durations, and PDF export |
| Hazard records | Causes, consequences, mitigation, and basic program validation |
| Reference catalogs | Units, measurements, regulations, regulatory requirements, and crew |
| Quality baseline | Automated model, matrix, Excel, and PDF tests; GitHub Actions workflow |

Data entry uses Django admin. There is no custom planning editor, homepage, or
program-selection page. Regulations, units, aircraft, and crew are stored, but
are not fully connected to certification, measurement validation, or operations.

Planned capabilities include aircraft configuration baselines, program membership
and authorization, controlled revisions and approvals, regulatory verification
links, hazard assessment approval, flight logs, execution attempts, results, and
compliance evidence. These are **not implemented**.

## Stack and architecture

- Python 3.13.9: local baseline recorded in `.python-version`.
- Django 5.2.18: server-rendered modular monolith and admin interface.
- SQLite: local development; tests use a separate in-memory database.
- openpyxl: Excel generation; ReportLab: PDF generation.
- python-dotenv: optional local environment loading.
- Development tools: pypdf for PDF inspection and coverage for line reports.

```text
config/           Project settings and root URLs
programs/         Program and aircraft models
testing/          Planning models, matrix, exports, and regression tests
reference_data/   Reference catalogs, crew, and program hazards
demo_data.json    Synthetic demonstration fixture
TESTING.md        Test design, commands, and manual PDF checks
```

Planning relationships follow Program → EngineeringTestRequirement → Test →
TestPoint → TestPointCondition. Cards belong to tests; sequences belong to
programs and contain ordered point/card assignments. A matrix is derived from
these records rather than stored separately.

## Developer setup

Use a local checkout and run the following commands from the directory containing
`manage.py`. Install Python 3.13, preferably the tested 3.13.9 baseline. CI uses
the available Python 3.13 patch release, which can differ from the local baseline.
An internet connection is required for dependency installation.

### 1. Create and activate a virtual environment

macOS/Linux:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python --version
```

Windows PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
```

If PowerShell blocks activation, use `.\.venv\Scripts\python.exe` in place of
`python` in the commands below. Activation selects an interpreter; it does not
change application configuration. Run `deactivate` when finished with an activated
environment.

### 2. Install dependencies

For development and the complete test suite:

```bash
python -m pip install -r requirements-dev.txt
python -m pip check
```

`requirements-dev.txt` includes `requirements.txt`, so this installs both runtime
and development dependencies. Runtime-only installation is
`python -m pip install -r requirements.txt`; PDF inspection tests and coverage
also require the development dependencies.

### 3. Configure the environment

For a **new checkout without an existing `.env`**, copy the example:

macOS/Linux:

```bash
if [ ! -e .env ]; then cp .env.example .env; fi
```

Windows PowerShell:

```powershell
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```

Preserve an existing `.env`. Generate a local secret and paste it into the file:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Replace the placeholder; never publish the generated secret. For local development:

```dotenv
DJANGO_SECRET_KEY=your-generated-local-secret
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,[::1]
DJANGO_LOAD_DOTENV=true
```

The example defaults to `DJANGO_DEBUG=false`; enable it only for local debugging.
Boolean values accept true/false, yes/no, on/off, or 1/0, ignoring case and outer
whitespace. Invalid values fail explicitly. Hosts are comma-separated, without
URL schemes or ports. A missing or empty normal secret prevents startup.

Process environment variables override `.env`. To disable file loading, set
`DJANGO_LOAD_DOTENV=false` in the process environment before starting Python.
Keep `.env` private; it and `db.sqlite3` are ignored by Git.

### 4. Create the local development database

For a new local development database:

```bash
python manage.py check
python manage.py migrate
```

Normal settings use `db.sqlite3` in the repository root. These commands are setup
instructions, not a reason to reset an existing database or migration history.

### 5. Load synthetic demo data (optional)

Use a fresh development database dedicated to demonstration data:

```bash
python manage.py loaddata demo_data.json
```

The fixture contains one synthetic program (ID `101`), two aircraft, twelve tests,
36 points, twelve cards, four sequences, conditions, and reference/hazard records.
It contains no user accounts. Loading fixtures writes records with fixed primary
keys and can overwrite matching records. Do not load it into engineering data
or assume repeated loading is a data-reset operation.

### 6. Create an admin user

```bash
python manage.py createsuperuser
```

Follow the prompts and choose your own credentials. No demonstration admin
password is provided. The superuser is for local administration.

### 7. Start the development server

```bash
python manage.py runserver 127.0.0.1:8000
```

Open:

- Admin: <http://127.0.0.1:8000/admin/>
- Demo matrix: <http://127.0.0.1:8000/testing/program/101/matrix/>
- Demo Excel: <http://127.0.0.1:8000/testing/program/101/matrix/export/>

The matrix includes an Excel download link. Card and sequence PDFs are available at
`/testing/card/<card_id>/export/pdf/` and
`/testing/sequence/<sequence_id>/export/pdf/`; obtain IDs from admin records.
Use the actual program ID for your own records. The root URL `/` has no homepage.
Stop the server with Ctrl+C. Django's development server is not a production host.

## Automated checks

With the virtual environment activated:

```bash
python manage.py test --settings=config.test_settings --verbosity=2 --noinput
python manage.py check --settings=config.test_settings
python manage.py makemigrations --check --dry-run --settings=config.test_settings
python -m coverage run manage.py test --settings=config.test_settings --verbosity=2 --noinput
python -m coverage report
```

Test settings skip `.env`, use a synthetic secret and an in-memory SQLite database,
and do not require demo loading or a superuser. Never serve the application with
test settings. See [TESTING.md](TESTING.md) for targeted commands and interpretation.

The Foundation baseline has 73 tests: **71 pass and two are expected failures**.
Counts change as tests are added. The expected failures record known defects;
a successful test run does not mean those defects are fixed.

## GitHub Actions CI

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs on pushes to `main` and
`feature/ftms-ai`, and pull requests targeting either branch. It uses Ubuntu,
Python 3.13, pinned requirement files, read-only contents permission, and a
10-minute timeout. It installs dependencies, runs `pip check`, Django checks,
migration drift detection, the complete suite, and a terminal coverage report.

CI requires no private `.env`, project secrets, or real engineering data. It does
not deploy. Coverage excludes tests and migration files; there is no coverage
percentage gate or uploaded coverage artifact. Hosted execution must be checked
in GitHub after the owner pushes; local checks do not establish hosted success.

## Known limitations and roadmap

- Custom matrix and export endpoints currently allow anonymous access; program
  filtering is not user authorization. Use synthetic data on public demos.
- Cross-program validation uses model `clean()`; direct `save()` and bulk writes
  can bypass it. Parent changes do not automatically validate descendants.
- Card points are inferred from sequence assignments; cards and sequences are
  mutable despite revision labels. No approval history or immutable release exists.
- Excel interprets formula-like text such as `=1+1` as a formula (expected failure).
- Oversized PDF table rows can raise `LayoutError` (expected failure).
- Exports omit some units, tolerances, point criteria, and referenced revisions.
  They are planning demonstrations, not controlled flight instructions.
- Some status values and identifiers lack constraints. Unit catalogs do not
  validate free-text point conditions. Font support and PDF layout need manual review.
- SQLite concurrency, production hosting, backups, and operational controls are
  not qualified by this test suite. No compliance claim is made.

Recommended progression: program authorization and data integrity → reliable
engineering exports and controlled revisions → configuration/certification/safety
links → flight operations and execution → reviewed results and evidence.
Retain the modular Django monolith and add capabilities incrementally.

## License

See [LICENSE](LICENSE).
