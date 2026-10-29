# FTMS testing guide

## Prerequisites and isolation

Use Python 3.13 and the virtual environment described in [README.md](README.md):

```bash
python -m pip install -r requirements-dev.txt
python -m pip check
```

All commands below run from the repository root with that environment activated.
Always select `config.test_settings`. It disables private `.env` loading and
supplies synthetic settings, an in-memory SQLite database, a fast test-only
password hasher, and an in-memory email backend.

Django creates the test schema from existing migrations and discards the test
database afterward. A log mentioning `file:memorydb_default` refers to SQLite's
shared in-memory test database, not the repository's `db.sqlite3`.
No demo fixture or local admin account is required. Do not use test settings to
serve the application, and do not run reset/flush commands on the local database
to prepare tests.

## Django TestCase and synthetic records

`django.test.TestCase` gives each test an isolated database state using
transactions. `setUpTestData()` creates class-level records that Django isolates
between tests. Tests can update those records without changing the next test's
starting state.

`testing/test_support.py` contains shared fixtures:

- `PlanningDataMixin`: two programs and their requirements, tests, points, cards,
  and sequences, without relying on specific primary keys.
- `MatrixDataMixin`: distinct program markers, conditions, target values, and
  ordering helpers for HTML, Excel, and PDF tests.
- `ConstraintAssertionsMixin`: validation and direct-write uniqueness assertions.

PDF-specific setup is in `testing/test_pdf_exports.py`. The suite does not load
the larger demo fixture. Its fixture installation is a separate setup smoke check,
not a committed automated test.

## Model validation versus database constraints

`instance.full_clean()` checks field values, custom model `clean()` methods,
uniqueness, and model constraints. `instance.save()` does not automatically call
`full_clean()`. Therefore a test expecting a validation error does not prove a
direct database write is protected.

Uniqueness tests verify both layers:

1. Construct a duplicate and require `ValidationError` from `full_clean()`.
2. Attempt a direct insert and require database `IntegrityError`.
3. Wrap the intentional failing insert inside `transaction.atomic()` so Django
   rolls back to a savepoint before the test continues using the database.

Cross-program checks are application validation, not database-wide guarantees or
user authorization. Tests also check allowed relationships, optional fields,
identifier reuse in valid scopes, sequence ordering, and protected deletions.
Existing `SET_NULL` behavior is tested as current behavior; it does not preserve
complete historical traceability.

## Test inventory

| Module | Scope |
|---|---|
| `programs/tests.py` | Aircraft/program and requirement relationships |
| `testing/tests.py` | Cross-program points, card compatibility, sequence validation, uniqueness, ordering, deletions |
| `reference_data/tests.py` | Hazard validation, scoped uniqueness, unit/measurement identity, protected references |
| `testing/test_matrix.py` | Real HTTP requests, filtering, lexical ordering, empty/404 cases, labels, zero/null targets, export link |
| `testing/test_excel_exports.py` | Workbook response, columns, filtering, values, conditions, empty exports, frozen header, filter, formula regression |
| `testing/test_pdf_exports.py` | Parsed card/sequence responses, identity, content, membership, duplicates, order, totals, optional data, multiline/markup, oversized rows |

Excel tests use openpyxl with `data_only=False` so formulas remain visible rather
than being hidden behind cached results. PDF tests use pypdf on actual response
bytes, require a valid PDF with at least one page, and inspect extracted text.
Text wrapping can insert whitespace into identifiers; short synthetic markers
avoid confusing wrapping with missing data. Text extraction does not prove visual
correctness or complete Unicode support.

## Run tests locally

Complete discovery, including all model and export tests:

```bash
python manage.py test --settings=config.test_settings --verbosity=2 --noinput
```

Model tests only:

```bash
python manage.py test programs.tests testing.tests reference_data.tests --settings=config.test_settings --verbosity=2
```

Selected presentation/export tests:

```bash
python manage.py test testing.test_matrix --settings=config.test_settings --verbosity=2
python manage.py test testing.test_excel_exports --settings=config.test_settings --verbosity=2
python manage.py test testing.test_pdf_exports --settings=config.test_settings --verbosity=2
```

A single case:

```bash
python manage.py test testing.tests.SequenceItemValidationTests.test_point_from_another_program_is_rejected --settings=config.test_settings --verbosity=2
```

CI-equivalent checks, after installing development dependencies:

```bash
python -m pip check
python manage.py check --settings=config.test_settings
python manage.py makemigrations --check --dry-run --settings=config.test_settings
python -m coverage run manage.py test --settings=config.test_settings --verbosity=2 --noinput
python -m coverage report
```

The migration command checks for differences between models and migration files;
it does not create migrations. These checks do not run deployment qualification.

`.coveragerc` measures application line coverage in `programs`, `testing`, and
`reference_data`, excluding migrations and tests. It does not measure settings,
template semantics, or branch coverage. There is no minimum percentage gate.
Expected-failure execution contributes to line coverage, so a high number is not
proof of correctness. The initial measured baseline was 96% line coverage.

## Expected failures and known defects

The current baseline is 73 discovered tests: 71 passing and two expected failures.
There should be no unexpected failures or errors.

| Regression | Intended behavior | Existing defect |
|---|---|---|
| `ExcelMatrixExportTests.test_formula_like_remarks_are_preserved_as_literal_text` | `=1+1` remains literal text (`data_type='s'`) | Export writes a formula (`data_type='f'`) |
| `TestSequencePDFTests.test_oversized_row_exports_without_losing_required_content` | Export succeeds with all required text and rows retained | ReportLab raises `LayoutError` for a row taller than the page |

These tests use `unittest.expectedFailure`. A known failure does not fail the suite;
an unexpected success does, reminding the developer to remove the marker after a
fix. A marker can also hide an unrelated failure inside its test, so inspect the
failure cause when changing surrounding code. Do not mark new failures expected
merely to make CI green, and do not fix oversized content by silently truncating it.

Unimplemented authorization, release history, or operational workflows are not
covered by these tests. Their absence is documented in the README rather than
represented as speculative expected failures.

## Manual PDF verification

Use a separate synthetic development database and the normal local settings.
Follow README setup, load demo data only into a fresh demonstration database,
start the development server, and obtain card/sequence IDs in admin.

Download:

- `/testing/card/<card_id>/export/pdf/`
- `/testing/sequence/<sequence_id>/export/pdf/`

Inspect the PDFs in a viewer and, when relevant, print-preview A4 pages:

1. Check program, document number, revision, and headings.
2. Check text wrapping, table alignment, clipping, and page margins.
3. Check headings near page boundaries, repeated table headers, and footers.
4. Compare procedures, safety notes, criteria, assigned points, execution order,
   and duration totals with the synthetic source records.
5. Check empty documents, optional values, multiline text, and literal `<`, `>`,
   and `&`. Review representative engineering symbols for missing glyphs.
6. Exercise ordinary multi-page documents and the known oversized-row case.
   Record rendering failures; the current oversized-row regression is unresolved.
7. Identify missing engineering fields explicitly. Targets, tolerances,
   point-specific criteria, and referenced card revisions are not consistently
   included in current PDFs. A successful download is not completeness approval.

Keep generated test artifacts synthetic. Visual inspection is not a release,
flight-safety approval, or certification-compliance finding.
