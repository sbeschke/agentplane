# agentplane Agents instructions

## Development environment

- `mise` is used to set up a development environment
- `uv` is used to manage Python dependencies
- Run all Python commands with `mise x --` prefix: for example, `mise x -- uv add somepackage`
- Some local development shortcuts:
    - Running tests: `mise x -- uv run python manage.py test`
    - Generating migrations: `mise x -- uv run python manage.py makemigrations`
    - Applying migrations: `mise x -- uv run python manage.py migrate`
