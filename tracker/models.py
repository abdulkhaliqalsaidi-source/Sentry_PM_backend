from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid

class Project(models.Model):
    name = models.CharField(max_length=100, unique=True)
    api_key = models.CharField(max_length=64, unique=True, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class PermissionGroup(models.Model):
    name = models.CharField(max_length=100, unique=True)
    # Core screens
    can_view_dashboard = models.BooleanField(default=True)
    can_view_issues = models.BooleanField(default=True)
    can_view_users = models.BooleanField(default=True)
    can_view_settings = models.BooleanField(default=True)
    # Issues actions
    can_delete_issues = models.BooleanField(default=False)
    # Project actions
    can_create_project = models.BooleanField(default=False)
    can_edit_project = models.BooleanField(default=False)
    can_delete_project = models.BooleanField(default=False)
    can_create_task = models.BooleanField(default=False)
    can_edit_task = models.BooleanField(default=True)
    can_delete_task = models.BooleanField(default=False)
    can_view_user_projects = models.BooleanField(default=False)
    # Project sub-screens
    can_view_backlog = models.BooleanField(default=True)
    can_view_reports = models.BooleanField(default=True)
    can_view_members = models.BooleanField(default=True)
    can_manage_members = models.BooleanField(default=False)
    can_view_chat = models.BooleanField(default=True)
    can_view_docs = models.BooleanField(default=True)
    can_create_doc = models.BooleanField(default=False)
    can_edit_doc = models.BooleanField(default=False)
    can_delete_doc = models.BooleanField(default=False)
    # Releases
    can_manage_releases = models.BooleanField(default=False)
    # Evaluations
    can_view_evaluations = models.BooleanField(default=False)
    can_manage_evaluations = models.BooleanField(default=False)
    can_view_performance = models.BooleanField(default=True)
    can_view_notifications = models.BooleanField(default=True)
    can_manage_permissions = models.BooleanField(default=False)
    # Sprints & Epics
    can_manage_sprints = models.BooleanField(default=False)
    can_manage_epics = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class User(AbstractUser):
    primary_project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name="developers")
    permission_group = models.ForeignKey(PermissionGroup, on_delete=models.SET_NULL, null=True, blank=True, related_name="users")
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)

class Issue(models.Model):
    title = models.CharField(max_length=255) # e.g. ZeroDivisionError
    hash_id = models.CharField(max_length=32, unique=True, db_index=True) # Fingerprint
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='issues', null=True, blank=True)
    status = models.CharField(max_length=20, default='open') # open, resolved
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    counter = models.IntegerField(default=1) # Occurrence count
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_issues')

    def __str__(self):
        return f"{self.title} ({self.counter})"

class Session(models.Model):
    session_id = models.CharField(max_length=100, unique=True, db_index=True)
    events_data = models.JSONField(default=list) # Stores rrweb events
    network_logs = models.JSONField(default=list, null=True, blank=True) # Captured network requests for the session
    console_logs = models.JSONField(default=list, null=True, blank=True) # Captured console output for the session
    started_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.session_id

class Event(models.Model):
    issue = models.ForeignKey(Issue, related_name='events', on_delete=models.CASCADE)
    session = models.ForeignKey(Session, related_name='error_events', on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    user_ident = models.CharField(max_length=100, null=True) # User identifier
    url = models.CharField(max_length=255, null=True)
    traceback = models.TextField() # Full stack trace
    breadcrumbs = models.JSONField(default=list) # User actions before error
    events_data = models.JSONField(default=list, null=True, blank=True) # rrweb events specific to this error
    network_logs = models.JSONField(default=list, null=True, blank=True) # Captured network requests
    console_logs = models.JSONField(default=list, null=True, blank=True) # Captured console output

    def __str__(self):
        return f"Event for {self.issue} at {self.timestamp}"
