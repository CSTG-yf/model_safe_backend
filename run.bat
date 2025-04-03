@echo off

set PROJECT_DIR=%~dp0

if not exist "%PROJECT_DIR%\.venv" (
    echo Creating virtual environment...
    E:\install\python3.11\python.exe -m venv .venv
)

call .venv\Scripts\activate

pip install --upgrade pip
pip install -r requirements.txt

python manage.py makemigrations
python manage.py migrate

start "" redis-server
timeout /t 2 /nobreak >nul && echo Waiting for Redis to start...

echo Clearing Redis tasks...
redis-cli FLUSHDB
timeout /t 1 /nobreak >nul

echo Starting Celery...
start "" cmd /k "call .venv\Scripts\activate && celery -A ai_evaluation worker --loglevel=info --pool=solo"

echo Starting Daphne...
start "" cmd /k "call .venv\Scripts\activate && daphne -b 127.0.0.1 -p 8000 ai_evaluation.asgi:application"

cmd /k