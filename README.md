# AI Evaluation Backend

## Local Setup

1. Create a Python 3.11+ virtual environment.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
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
   python manage.py migrate
   ```

6. Start the backend:

   ```bash
   python manage.py runserver 127.0.0.1:8000
   ```

   Or use `run.bat` if the local Python path inside that script has been adjusted.

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
