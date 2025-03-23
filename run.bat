@echo off

set PROJECT_DIR=%~dp0

if not exist "%PROJECT_DIR%\.venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate

pip install --upgrade pip
pip install -r requirements.txt

python manage.py makemigrations
python manage.py migrate

start "" redis-server

start "" celery -A ai_evaluation worker --loglevel=info --pool=solo

start "" daphne -b 127.0.0.1 -p 8000 ai_evaluation.asgi:application

cmd /k