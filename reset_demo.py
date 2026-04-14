"""
Sentry PM — Demo Reset Script
================================
Resets all demo data back to its original state.
Useful for live demo environments.

    python reset_demo.py

WARNING: This will delete ALL projects, tasks, and evaluations
         but will keep the user accounts.
"""

import os, sys, django
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, str(BASE_DIR))
django.setup()

GREEN = "\033[92m"; RED = "\033[91m"; YELLOW = "\033[93m"; RESET = "\033[0m"; BOLD = "\033[1m"

def confirm():
    print(f"\n{YELLOW}{BOLD}  ⚠  WARNING: This will delete all projects, tasks, and evaluations!{RESET}")
    print(f"  Type '{BOLD}RESET{RESET}' to confirm: ", end='')
    ans = input().strip()
    if ans != 'RESET':
        print(f"\n{RED}  Aborted.{RESET}\n")
        sys.exit(0)

def reset():
    print(f"\n{BOLD}  Resetting demo data...{RESET}")
    try:
        from project_management.models import (
            Project, Sprint, Task, Epic, EvaluationPeriod,
            DeveloperEvaluation, Notification, ProjectMember
        )
        Notification.objects.all().delete()
        DeveloperEvaluation.objects.all().delete()
        EvaluationPeriod.objects.all().delete()
        Task.objects.all().delete()
        Sprint.objects.all().delete()
        Epic.objects.all().delete()
        ProjectMember.objects.all().delete()
        Project.objects.all().delete()
        print(f"{GREEN}  ✔  All project data cleared.{RESET}")
    except Exception as e:
        print(f"{YELLOW}  ⚠  Partial reset: {e}{RESET}")

    # Re-run demo data
    print(f"\n{BOLD}  Reloading demo data...{RESET}\n")
    import demo_data
    demo_data.users = demo_data.create_users()
    demo_data.create_projects(demo_data.users)
    demo_data.create_evaluations(demo_data.users)
    demo_data.create_notifications(demo_data.users)
    print(f"\n{GREEN}{BOLD}  ✅  Demo reset complete!{RESET}\n")

if __name__ == '__main__':
    confirm()
    reset()
