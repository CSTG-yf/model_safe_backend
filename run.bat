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

python manage.py runserver

cmd /k
