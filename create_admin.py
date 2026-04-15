import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from tracker.models import User

username = os.environ.get('ADMIN_USERNAME', 'admin')
email    = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
password = os.environ.get('ADMIN_PASSWORD', 'admin123')

user, created = User.objects.get_or_create(username=username)
user.email = email
user.is_staff = True
user.is_superuser = True
user.set_password(password)
user.save()

if created:
    print(f"Superuser '{username}' created.")
else:
    print(f"Superuser '{username}' updated.")

# Auto-create default statuses for projects that don't have any
from project_management.models import Project, TaskStatus

STATUS_DEFAULTS = [
    {'name': 'To Do',       'category': 'TO_DO',       'color': '#64748B', 'order': 1},
    {'name': 'In Progress', 'category': 'IN_PROGRESS',  'color': '#3B82F6', 'order': 2},
    {'name': 'Pending',     'category': 'PENDING',      'color': '#F59E0B', 'order': 3},
    {'name': 'In Review',   'category': 'IN_REVIEW',    'color': '#8B5CF6', 'order': 4},
    {'name': 'Done',        'category': 'DONE',         'color': '#10B981', 'order': 5},
]

for project in Project.objects.all():
    if not TaskStatus.objects.filter(project=project).exists():
        for s in STATUS_DEFAULTS:
            TaskStatus.objects.create(project=project, **s)
        print(f"Created default statuses for project: {project.name}")
