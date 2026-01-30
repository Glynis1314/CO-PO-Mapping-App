# Development Setup (Windows & Bash)

Follow the steps below to create a local dev environment and start the Django project.

## Windows (PowerShell)

1. Open PowerShell and navigate to the project root (the folder with `manage.py`).

2. Create and activate a virtual environment:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

3. Upgrade pip and install dependencies:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

4. Run migrations and seed initial data:

```powershell
python manage.py migrate
python manage.py seed_initial
```

5. Create a superuser (follow prompts):

```powershell
python manage.py createsuperuser
```

6. Start the dev server:

```powershell
python manage.py runserver
```

Open http://127.0.0.1:8000/ in your browser.

---

## Bash (Linux / macOS / Git Bash on Windows)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_initial
python manage.py createsuperuser
python manage.py runserver
```

---

## Running tests

```bash
python manage.py test
```

---

## Notes
- The repository includes `scripts/setup_dev_env.ps1` to automate steps for PowerShell.
- If you plan to import Excel (`.xlsx`) files, `openpyxl` is required (included in `requirements.txt`).
- For production, replace SQLite with PostgreSQL and use a proper background worker (Celery + Redis) for imports and long-running tasks.