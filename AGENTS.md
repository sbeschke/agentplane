# agentplane Agents instructions

## Development environment

- `uv` is used for dependency management and environment setup
- Run all Python commands with `uv run` prefix: for example, `uv run python manage.py runserver`
- The project uses Django
    - Running a development server: `uv run python manage.py runserver`
    - Generating migrations: `uv run python manage.py makemigrations`
    - Applying migrations: `uv run python manage.py migrate`
