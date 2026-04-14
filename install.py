"""
Sentry PM — Automated Installation Script
==========================================
Run this script once to set up the project:

    python install.py

It will:
  1. Copy .env.example → .env (if not exists)
  2. Install Python dependencies
  3. Run database migrations
  4. Create an admin superuser (admin / admin123)
  5. Load demo data
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# ── Colours ──────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BLUE   = "\033[94m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg):   print(f"{GREEN}  ✔  {msg}{RESET}")
def warn(msg): print(f"{YELLOW}  ⚠  {msg}{RESET}")
def err(msg):  print(f"{RED}  ✘  {msg}{RESET}")
def info(msg): print(f"{BLUE}  →  {msg}{RESET}")
def title(msg):print(f"\n{BOLD}{BLUE}{'═'*55}\n  {msg}\n{'═'*55}{RESET}")


def run(cmd, cwd=None):
    """Run a shell command and return success status."""
    result = subprocess.run(cmd, shell=True, cwd=cwd or BASE_DIR)
    return result.returncode == 0


def step1_env():
    title("Step 1 — Environment Configuration")
    env_file    = BASE_DIR / '.env'
    env_example = BASE_DIR / '.env.example'

    if env_file.exists():
        warn(".env already exists — skipping copy.")
    else:
        if not env_example.exists():
            err(".env.example not found! Cannot continue.")
            sys.exit(1)
        shutil.copy(env_example, env_file)
        ok("Copied .env.example → .env")
        warn("Please review .env and update your settings if needed.")
        print(f"\n  {YELLOW}Press ENTER to continue after reviewing .env ...{RESET}")
        input()


def step2_dependencies():
    title("Step 2 — Python Dependencies")
    req_file = BASE_DIR / 'requirements.txt'
    if not req_file.exists():
        err("requirements.txt not found!")
        sys.exit(1)
    info("Installing Python packages...")
    if not run(f'"{sys.executable}" -m pip install -r requirements.txt'):
        err("Failed to install dependencies. Check your Python environment.")
        sys.exit(1)
    ok("Dependencies installed.")


def step3_migrate():
    title("Step 3 — Database Migrations")
    info("Running migrations...")
    if not run(f'"{sys.executable}" manage.py migrate --run-syncdb'):
        err("Migration failed. Check your database settings in .env")
        sys.exit(1)
    ok("Database is ready.")


def step4_superuser():
    title("Step 4 — Admin Account")
    info("Creating admin user (admin / admin123)...")

    script = """
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from tracker.models import User
if not User.objects.filter(username='admin').exists():
    u = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    u.first_name = 'System'
    u.last_name  = 'Admin'
    u.save()
    print('CREATED')
else:
    print('EXISTS')
"""
    result = subprocess.run(
        [sys.executable, '-c', script],
        cwd=BASE_DIR, capture_output=True, text=True
    )
    if 'CREATED' in result.stdout:
        ok("Admin user created → username: admin | password: admin123")
    elif 'EXISTS' in result.stdout:
        warn("Admin user already exists — skipped.")
    else:
        warn(f"Could not create admin: {result.stderr.strip()}")


def step5_demo_data():
    title("Step 5 — Demo Data")
    demo_script = BASE_DIR / 'demo_data.py'
    if not demo_script.exists():
        warn("demo_data.py not found — skipping demo data.")
        return
    info("Loading demo data (projects, tasks, users)...")
    if not run(f'"{sys.executable}" demo_data.py'):
        warn("Demo data loading had issues — check output above.")
    else:
        ok("Demo data loaded successfully.")


def step6_frontend():
    title("Step 6 — Frontend Build")
    fe_dir = BASE_DIR / 'frontend'
    if not fe_dir.exists():
        warn("frontend/ directory not found — skipping.")
        return

    info("Installing Node.js dependencies...")
    if not run('npm install', cwd=fe_dir):
        warn("npm install failed. Ensure Node.js 18+ is installed.")
        return
    ok("Node.js dependencies installed.")
    info("Running development server is available via: npm run dev")


def finish():
    title("✅  Installation Complete!")
    print(f"""
{GREEN}{BOLD}  Sentry PM is ready to run!{RESET}

  {BOLD}Backend:{RESET}
    python manage.py runserver

  {BOLD}Frontend:{RESET}
    cd frontend && npm run dev

  {BOLD}Demo Credentials:{RESET}
    Admin  →  username: admin   | password: admin123
    User   →  username: devuser | password: dev12345

  {BOLD}Documentation:{RESET}
    Open documentation/index.html in your browser

{BLUE}{'═'*55}{RESET}
""")


if __name__ == '__main__':
    print(f"""
{BOLD}{BLUE}
  ╔═══════════════════════════════════════════════╗
  ║       Sentry PM — Installation Wizard         ║
  ║   Project Management & Error Tracking v1.0    ║
  ╚═══════════════════════════════════════════════╝
{RESET}""")
    step1_env()
    step2_dependencies()
    step3_migrate()
    step4_superuser()
    step5_demo_data()
    step6_frontend()
    finish()
