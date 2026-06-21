# django-mops Agents instructions

- django-mops is a Python 3 project packaged as a Django app.
- `mise` is used for commands and tool installation
- `uv` is used for dependency management

## Ground Rules

- Always run the linter after making code changes: `mise run lint`
- All functionality should be covered by unit tests (where applicable) and API integration tests.
- **ALWAYS test before committing / pushing something**
- Make sure that tests pass and there are no linter errors before reporting completion on any task.
- If you need to run a Python command, prefix `uv run`.

## CI Testing

**For autonomous web agents (like me):**
- GitHub Actions CI runs tests against PostgreSQL automatically on push/PR
- **ALWAYS check CI status** after pushing - if tests fail, fix them immediately
- CI workflow: `.github/workflows/test.yml`
- CI uses `pgvector/pgvector:pg17` container with PostgreSQL
- To debug CI failures locally: `mise run test` (requires Docker for PostgreSQL)

## Development environment

- `mise` is used to set up a development environment
- `uv` is used to manage Python dependencies
- Run all Python commands with `mise x --` prefix: for example, `mise x -- uv add somepackage`
- Some local development shortcuts:
    - First-time setup: `mise run init` (tools, Python deps, migrations, prek hooks, llama-server runtime, local GGUF weights)
    - Running the app: `mise run dev` (Django, background worker, and `llama-server` on port 8765)
    - Running tests: `mise x -- uv run python manage.py test`
    - Generating migrations: `mise x -- uv run python manage.py makemigrations`
    - Applying migrations: `mise x -- uv run python manage.py migrate`

## Testing
- Django's test `Client` does not support DRF's `format="multipart"` parameter. Use standard multipart encoding by passing `SimpleUploadedFile` directly in the data dict.
- `django-tasks` uses `.enqueue()` method, not `.delay()` (which is Celery-style). Use `task.enqueue(args)` for background tasks.

## Running Tests

### Local development (requires Docker):
```bash
mise run test           # Run all tests with PostgreSQL
mise run test -v 2      # Verbose output
mise run test mops.tests.test_models  # Run specific tests
```

### Manual PostgreSQL setup (if not using mise):
```bash
# Start PostgreSQL with pgvector
docker run -d --rm --name mops-postgres -p 55432:5432 \
  -e POSTGRES_USER=mops -e POSTGRES_PASSWORD=mops -e POSTGRES_DB=mops \
  pgvector/pgvector:pg17

# Run tests
DATABASE_URL="postgresql://mops:mops@localhost:55432/mops" \
  python manage.py test
```

### CI (GitHub Actions):
- Automatically runs on push to `main` and `vibe/*` branches
- Automatically runs on PRs targeting `main`
- Uses PostgreSQL with pgvector extension
- Tests run in Ubuntu container with Python 3.12
