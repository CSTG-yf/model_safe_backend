import tkinter as tk
from tkinter import messagebox
import subprocess
import os
import sys
import json
from pathlib import Path

PROJECT_DIR = Path(__file__).parent


def create_base_environment():
    try:
        # Check if virtual environment exists
        venv_dir = PROJECT_DIR / ".venv"
        if not venv_dir.exists():
            messagebox.showinfo("Info", "Creating virtual environment...")
            subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)

        # Activate venv and upgrade pip + install requirements
        pip_path = str(venv_dir / "Scripts" / "pip")
        requirements_path = str(PROJECT_DIR / "requirements.txt")

        messagebox.showinfo("Info", "Upgrading pip and installing requirements...")
        subprocess.run([pip_path, "install", "--upgrade", "pip"], check=True)
        subprocess.run([pip_path, "install", "-r", requirements_path], check=True)

        messagebox.showinfo("Success", "Base environment setup completed!")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"Failed to create base environment: {e}")


def run_migrations():
    try:
        venv_dir = PROJECT_DIR / ".venv"
        python_path = str(venv_dir / "Scripts" / "python")

        messagebox.showinfo("Info", "Running migrations...")
        subprocess.run([python_path, "manage.py", "makemigrations"], check=True)
        subprocess.run([python_path, "manage.py", "migrate"], check=True)

        messagebox.showinfo("Success", "Migrations completed!")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"Failed to run migrations: {e}")


def import_data():
    try:
        data_path = PROJECT_DIR / "data.json"
        if not data_path.exists():
            messagebox.showerror("Error", f"data.json not found at {data_path}")
            return

        venv_dir = PROJECT_DIR / ".venv"
        python_path = str(venv_dir / "Scripts" / "python")

        # Check if the data import command exists in your Django project
        # You might need to adjust this depending on how you import data
        messagebox.showinfo("Info", "Importing data from data.json...")
        subprocess.run([python_path, "manage.py", "loaddata", str(data_path)], check=True)

        messagebox.showinfo("Success", "Data imported successfully!")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"Failed to import data: {e}")


def run_services():
    try:
        venv_dir = PROJECT_DIR / ".venv"
        python_path = str(venv_dir / "Scripts" / "python")

        messagebox.showinfo("Info", "Starting services...")

        # Start Redis
        subprocess.Popen(["redis-server"], creationflags=subprocess.CREATE_NEW_CONSOLE)

        # Start Celery
        subprocess.Popen([python_path, "-m", "celery", "-A", "ai_evaluation", "worker",
                          "--loglevel=info", "--pool=solo"],
                         creationflags=subprocess.CREATE_NEW_CONSOLE)

        # Start Daphne
        subprocess.Popen([python_path, "-m", "daphne", "-b", "127.0.0.1",
                          "-p", "8000", "ai_evaluation.asgi:application"],
                         creationflags=subprocess.CREATE_NEW_CONSOLE)

        messagebox.showinfo("Success", "Services started in separate consoles!")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start services: {e}")


def create_gui():
    root = tk.Tk()
    root.title("Django Project Manager")
    root.geometry("400x300")

    # Styling
    button_style = {
        "font": ("Arial", 10),
        "width": 30,
        "height": 2,
        "bg": "#f0f0f0",
        "activebackground": "#e0e0e0"
    }

    tk.Label(root, text="Select an action:", font=("Arial", 12, "bold")).pack(pady=10)

    # Button 1: Create Base Environment
    btn1 = tk.Button(root, text="1. Create Base Environment & Install Packages",
                     command=create_base_environment, **button_style)
    btn1.pack(pady=5)

    # Button 2: Run Migrations
    btn2 = tk.Button(root, text="2. Run Database Migrations",
                     command=run_migrations, **button_style)
    btn2.pack(pady=5)

    # Button 3: Import Data
    btn3 = tk.Button(root, text="3. Import Data from data.json",
                     command=import_data, **button_style)
    btn3.pack(pady=5)

    # Button 4: Run Services
    btn4 = tk.Button(root, text="4. Run All Services (Redis, Celery, Daphne)",
                     command=run_services, **button_style)
    btn4.pack(pady=5)

    root.mainloop()


if __name__ == "__main__":
    create_gui()
