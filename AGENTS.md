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
