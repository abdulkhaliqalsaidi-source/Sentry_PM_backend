"""
Sentry PM — Demo Data Seeder
==============================
Creates realistic demo data for showcasing all system features.
Run after install.py:

    python demo_data.py

Creates:
  • 4 demo users with different roles
  • 3 projects with full data
  • Active sprints with Kanban tasks
  • Developer evaluations
  • Notifications
"""

import os
import sys
import django
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, str(BASE_DIR))
django.setup()

from django.utils import timezone
from datetime import timedelta, date
from tracker.models import User

# ── Colours ──────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"; YELLOW = "\033[93m"; BLUE = "\033[94m"
BOLD   = "\033[1m";  RESET  = "\033[0m"
def ok(m):   print(f"{GREEN}  ✔  {m}{RESET}")
def info(m): print(f"{BLUE}  →  {m}{RESET}")
def skip(m): print(f"{YELLOW}  ⚡  {m}{RESET}")


# ─────────────────────────────────────────────────────────────────────────────
# 1. USERS
# ─────────────────────────────────────────────────────────────────────────────
def create_users():
    info("Creating demo users...")
    users_data = [
        dict(username='admin',   password='admin123',  first_name='System',  last_name='Admin',   email='admin@example.com',   is_staff=True, is_superuser=True),
        dict(username='devuser', password='dev12345',  first_name='Ahmed',   last_name='Al-Rashid',email='dev@example.com',    is_staff=False, is_superuser=False),
        dict(username='sarah',   password='sara12345', first_name='Sarah',   last_name='Johnson', email='sarah@example.com',   is_staff=False, is_superuser=False),
        dict(username='omar',    password='omar12345', first_name='Omar',    last_name='Hassan',  email='omar@example.com',    is_staff=False, is_superuser=False),
    ]
    created = {}
    for d in users_data:
        pw = d.pop('password')
        is_super = d.pop('is_superuser')
        is_staff = d.pop('is_staff')
        user, was_created = User.objects.get_or_create(username=d['username'], defaults=d)
        if was_created:
            user.set_password(pw)
            user.is_staff = is_staff
            user.is_superuser = is_super
            user.save()
            ok(f"User created: {user.username}")
        else:
            skip(f"User already exists: {user.username}")
        created[d['username']] = user
    return created


# ─────────────────────────────────────────────────────────────────────────────
# 2. PROJECTS, SPRINTS, TASKS
# ─────────────────────────────────────────────────────────────────────────────
def create_projects(users):
    info("Creating demo projects...")

    try:
        from project_management.models import (
            Project, ProjectMember, Sprint, Task, Epic, PermissionGroup
        )
    except ImportError as e:
        print(f"{YELLOW}  Skipping project data (model import error): {e}{RESET}")
        return

    admin = users['admin']
    dev   = users['devuser']
    sarah = users.get('sarah')
    omar  = users.get('omar')

    now = timezone.now().date()

    projects_data = [
        {
            'name': 'E-Commerce Platform',
            'description': 'A full-featured e-commerce platform with payment integration, inventory management, and real-time analytics.',
            'members': [admin, dev, sarah],
            'epics': ['Authentication', 'Product Catalog', 'Payment Gateway', 'Admin Dashboard'],
            'tasks': [
                ('User Login & Registration', 'in_progress', dev,   'high',   'story'),
                ('Product Listing Page',     'done',        sarah,  'medium', 'story'),
                ('Shopping Cart Logic',      'in_progress', dev,    'urgent', 'task'),
                ('Stripe Payment Integration','to_do',      sarah,  'critical','task'),
                ('Order History Screen',     'to_do',       omar,   'medium', 'story'),
                ('Fix 500 Error on Checkout','in_progress', dev,    'urgent', 'bug'),
            ],
        },
        {
            'name': 'Mobile App Backend',
            'description': 'REST API backend for the iOS and Android applications, featuring real-time notifications and offline sync.',
            'members': [admin, omar, dev],
            'epics': ['API Design', 'Push Notifications', 'Offline Mode'],
            'tasks': [
                ('API Rate Limiting',     'done',        omar,  'high',   'task'),
                ('Push Notification Setup','in_progress', dev,   'high',   'task'),
                ('User Profile Endpoint', 'done',        omar,  'medium', 'story'),
                ('Crash on iOS 17',       'in_progress', dev,   'critical','bug'),
                ('Offline Data Sync',     'to_do',       omar,  'medium', 'task'),
            ],
        },
        {
            'name': 'Analytics Dashboard',
            'description': 'Business intelligence dashboard with real-time charts, custom reports, and automated data pipelines.',
            'members': [admin, sarah, omar],
            'epics': ['Data Pipeline', 'Chart Components', 'Report Engine'],
            'tasks': [
                ('Revenue Chart Component', 'done',        sarah, 'high',   'story'),
                ('CSV Export Feature',      'done',        omar,  'medium', 'task'),
                ('Date Range Filter',       'in_progress', sarah, 'medium', 'task'),
                ('PDF Report Generator',    'to_do',       omar,  'high',   'task'),
                ('Data refresh lag bug',    'to_do',       sarah, 'high',   'bug'),
            ],
        },
    ]

    # Create a default permission group if none exists
    perm_group = None
    try:
        perm_group, _ = PermissionGroup.objects.get_or_create(
            name='Default',
            defaults={'permissions': {
                'view_dashboard': True, 'view_issues': True,
                'view_backlog': True,   'create_task': True,
            }}
        )
    except Exception:
        pass

    for pdata in projects_data:
        project, created = Project.objects.get_or_create(
            name=pdata['name'],
            defaults={'description': pdata['description'], 'owner': admin}
        )
        if created:
            ok(f"Project: {project.name}")
        else:
            skip(f"Project exists: {project.name}")
            continue

        # Add members
        for user in pdata['members']:
            role = 'admin' if user == admin else 'member'
            ProjectMember.objects.get_or_create(project=project, user=user, defaults={'role': role})
            if perm_group:
                try:
                    user.permission_group = perm_group
                    user.save()
                except Exception:
                    pass

        # Create sprint
        sprint, _ = Sprint.objects.get_or_create(
            project=project, name=f"{project.name} - Sprint 1",
            defaults={
                'start_date': now - timedelta(days=7),
                'end_date':   now + timedelta(days=7),
                'status':     'active',
            }
        )

        # Create epic and tasks
        epic = None
        if pdata['epics']:
            try:
                epic, _ = Epic.objects.get_or_create(
                    project=project, name=pdata['epics'][0],
                    defaults={'color': '#6366f1'}
                )
            except Exception:
                pass

        status_map = {
            'to_do': 'To Do', 'in_progress': 'In Progress',
            'done': 'Done', 'pending': 'Pending'
        }
        for i, (title, status, assignee, priority, issue_type) in enumerate(pdata['tasks']):
            Task.objects.get_or_create(
                project=project, title=title,
                defaults={
                    'status':      status_map.get(status, 'To Do'),
                    'assigned_to': assignee,
                    'priority':    priority,
                    'issue_type':  issue_type,
                    'sprint':      sprint,
                    'epic':        epic,
                    'story_points': (i % 5) + 1,
                    'reporter':    admin,
                }
            )
        ok(f"  → {len(pdata['tasks'])} tasks created for {project.name}")


# ─────────────────────────────────────────────────────────────────────────────
# 3. EVALUATIONS
# ─────────────────────────────────────────────────────────────────────────────
def create_evaluations(users):
    info("Creating developer evaluations...")
    try:
        from project_management.models import EvaluationPeriod, DeveloperEvaluation
    except ImportError:
        skip("Evaluation models not found — skipping.")
        return

    admin = users['admin']
    now   = timezone.now().date()

    period, created = EvaluationPeriod.objects.get_or_create(
        name='Q1 2026 Evaluation',
        defaults={
            'start_date': now - timedelta(days=90),
            'end_date':   now,
            'is_active':  True,
            'created_by': admin,
        }
    )

    eval_data = [
        (users['devuser'], 88, 'Excellent work on the API integration. Consistently meets deadlines.'),
        (users.get('sarah'), 92, 'Outstanding performance. Strong frontend skills and team collaboration.'),
        (users.get('omar'), 76, 'Good progress. Needs improvement in code documentation and testing.'),
    ]

    for user, score, notes in eval_data:
        if not user:
            continue
        DeveloperEvaluation.objects.get_or_create(
            period=period, developer=user,
            defaults={'score': score, 'notes': notes, 'evaluated_by': admin}
        )
        ok(f"Evaluation: {user.get_full_name()} — {score}/100")


# ─────────────────────────────────────────────────────────────────────────────
# 4. NOTIFICATIONS
# ─────────────────────────────────────────────────────────────────────────────
def create_notifications(users):
    info("Creating sample notifications...")
    try:
        from project_management.models import Notification
    except ImportError:
        skip("Notification model not found — skipping.")
        return

    admin = users['admin']
    dev   = users['devuser']
    sarah = users.get('sarah')

    notifs = [
        (dev,   admin,  'assigned',  'Ahmed Al-Rashid assigned you to "Fix 500 Error on Checkout"'),
        (dev,   admin,  'mentioned', 'Ahmed Al-Rashid mentioned you in a comment on the Sprint task.'),
        (sarah, admin,  'commented', 'Sarah Johnson commented on "Stripe Payment Integration"'),
        (admin, dev,    'assigned',  'You were assigned to "Shopping Cart Logic" by System Admin'),
    ]
    for recipient, sender, verb, desc in notifs:
        if not recipient or not sender:
            continue
        Notification.objects.get_or_create(
            recipient=recipient, verb=verb, description=desc,
            defaults={'actor': sender, 'is_read': False}
        )
    ok(f"Created {len(notifs)} sample notifications.")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print(f"\n{BOLD}{BLUE}  Sentry PM — Loading Demo Data{RESET}\n  {'─'*40}")
    users = create_users()
    create_projects(users)
    create_evaluations(users)
    create_notifications(users)
    print(f"\n{GREEN}{BOLD}  ✅  Demo data loaded successfully!{RESET}")
    print(f"""
  Demo Accounts:
  ┌─────────────┬──────────────┬──────────────┐
  │  Username   │   Password   │    Role      │
  ├─────────────┼──────────────┼──────────────┤
  │  admin      │  admin123    │  Super Admin │
  │  devuser    │  dev12345    │  Developer   │
  │  sarah      │  sara12345   │  Developer   │
  │  omar       │  omar12345   │  Developer   │
  └─────────────┴──────────────┴──────────────┘
""")
