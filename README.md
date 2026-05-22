# AI Evaluation Backend

## Local Setup

1. Install uv and use Python 3.11.
2. Install dependencies:

   ```bash
   uv sync
   ```

3. Copy `.env.example` to `.env` and fill in local values:

   ```bash
   copy .env.example .env
   ```

4. Configure at least:

   - `DJANGO_SECRET_KEY`
   - `DB_NAME`
   - `DB_USER`
   - `DB_PASSWORD`
   - `REDIS_URL`
   - `ONE_API_BASE_URL`
   - `ONE_API_KEY`

5. Run migrations:

   ```bash
   uv run python manage.py migrate
   ```

6. Start the backend:

   ```bash
   uv run python manage.py runserver 127.0.0.1:8000
   ```

   Or use `run.bat` if the local Python path inside that script has been adjusted.

## Dependency Management

- If the default Windows uv cache has permission issues, set a project-local cache:

  ```powershell
  $env:UV_CACHE_DIR = ".uv-cache"
  ```

- `pyproject.toml` is the source of truth for Python dependencies.
- `uv.lock` pins the resolved dependency graph for repeatable installs.
- Use `uv add package-name` to add a dependency.
- Use `uv remove package-name` to remove a dependency.
- Use `uv lock` after manual dependency edits.
- Keep `requirements.txt` only as a compatibility export for older scripts:

  ```bash
  uv export --format requirements-txt --no-hashes -o requirements.txt
  ```

## Docker Setup

Run the full backend stack:

```bash
docker compose up --build
```

The Docker image installs dependencies with uv into `/opt/venv`. This avoids conflicts when the project source is bind-mounted into `/app`.

## Runtime Services

- Django REST API: `http://127.0.0.1:8000/api/`
- Redis is used for cache, Channels, and Celery state.
- Celery should use `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` from `.env`.

## Configuration Notes

- Do not commit `.env`, real API keys, database passwords, Redis dumps, generated reports, or local virtual environments.
- Public endpoints should be limited to registration and login. Project, question bank, evaluation, jailbreak, and report APIs require authentication and project membership.
- Logs are written to `logs/app.log` and stdout.

## First-Stage Refactor Status

- Configuration is environment-variable based.
- `ONE_API_KEY` is no longer hard-coded.
- API responses have a shared exception envelope with `code`, `message`, `data`, and optional `request_id`.
- Request IDs are added through middleware and returned as `X-Request-ID`.
- Core project-scoped APIs now require authenticated project membership.
