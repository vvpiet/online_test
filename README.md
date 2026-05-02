# Engineering College Online MCQ Test App

A Streamlit-based online MCQ testing system for engineering college students and administrators.

## Features
- Admin and student user roles
- Admin can configure IP address restrictions for exam access
- Admin can upload branch/semester MCQ papers from CSV/Excel files
- Admin can add student accounts and generate passwords
- Timer configuration for exams (30-90 minutes)
- Timetable entries to activate question papers at scheduled times
- Student proctoring helpers with camera preview and tab-switch warning
- Downloadable results filtered by branch/class

## Installation

1. Create and activate a Python virtual environment.
2. Install requirements in a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

> For cloud deploys, use `python-3.12.18` via `runtime.txt` to avoid Python 3.14 build issues.

> Make sure `runtime.txt` and `pyproject.toml` are committed and pushed to GitHub before redeploying.

3. Configure Postgres database connection.

Set the `DATABASE_URL` environment variable, for example:

```powershell
$env:DATABASE_URL = 'postgresql://postgres:postgres@localhost:5432/online_test'
```

4. Run the app:

```powershell
.\.venv\Scripts\streamlit run app.py
```

## Admin login
- Default admin account: `admin`
- Default password: `admin123`

> Change the default password immediately after the first login.

## Question upload format
The upload file must contain these columns:
- `question`
- `option_a`
- `option_b`
- `option_c`
- `option_d`
- `answer_key`

## Notes
- Student accounts are created by the admin.
- Passwords are stored hashed using bcrypt.
- Results are available immediately after exam submission.
- IP restriction is implemented by allowed IP list and browser-based IP detection.
