CO-PO Mapping — Django app

Short description

This repository contains a Django application to map Course Outcomes (CO) to Program Outcomes (PO) and to calculate attainment from uploaded marks and surveys.

Quick start (development)

1. Create and activate a virtualenv
   - Windows (PowerShell):
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1

2. Install dependencies
   pip install -r requirements.txt

3. Copy the example .env and provide real values
   cp .env.example .env
   (edit `.env` and set DJANGO_SECRET_KEY, DJANGO_DEBUG, etc.)

4. Run migrations and start server
   python manage.py migrate
   python manage.py runserver

Environment / secrets (do NOT commit `.env`)

- DJANGO_SECRET_KEY — Django secret key (required in production)
- DJANGO_DEBUG — True/False
- DJANGO_ALLOWED_HOSTS — comma-separated hosts
- DATABASE_URL — optional (e.g. sqlite:///db.sqlite3 or postgres://...)

CI / production

- Store sensitive values in your CI provider (GitHub Actions Secrets) or cloud secret manager.
- Never store production secrets in the repository.

Repository hygiene & recommended next steps

- Replace the placeholder SECRET in `.env` before deploying.
- Remove committed local database from git if present: `git rm --cached db.sqlite3 && git commit -m "remove local DB"`
- Add project-specific docs to `docs/`.

Where to edit core pieces

- Business logic: `attainment/utils/attainment_engine.py`
- Views / templates: `attainment/views.py`, `templates/`
- Settings: `coAtttainemnt/settings.py`

License

This repository is licensed under the MIT license (see `LICENSE`).