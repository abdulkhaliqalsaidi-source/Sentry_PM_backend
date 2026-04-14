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
