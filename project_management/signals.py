from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from tracker.models import Issue
from .models import Project, Task

User = get_user_model()

@receiver(post_save, sender=Project)
def create_default_statuses(sender, instance, created, **kwargs):
    """Auto-create default TaskStatuses when a new Project is created."""
    if created:
        from .models import TaskStatus
        defaults = [
            {'name': 'To Do',       'category': 'TO_DO',       'color': '#64748B', 'order': 1},
            {'name': 'In Progress', 'category': 'IN_PROGRESS',  'color': '#3B82F6', 'order': 2},
            {'name': 'Done',        'category': 'DONE',         'color': '#10B981', 'order': 3},
        ]
        for s in defaults:
            TaskStatus.objects.get_or_create(
                project=instance, name=s['name'],
                defaults={'category': s['category'], 'color': s['color'], 'order': s['order']}
            )


@receiver(post_save, sender=Issue)
def create_project_from_issue(sender, instance, created, **kwargs):
    """
    When a new Issue is created, ensure a corresponding Project exists in Project Management.
    The Issue model has a 'project' foreign key to tracker.models.Project.
    """
    if created and instance.project:
        project_name = instance.project.name
        
        # Check if project already exists in PM
        if not Project.objects.filter(name=project_name).exists():
            # Get default owner (admin)
            try:
                admin_user = User.objects.get(pk=1)
            except User.DoesNotExist:
                admin_user = User.objects.filter(is_superuser=True).first()
            
            if admin_user:
                Project.objects.create(
                    name=project_name,
                    description=f"Auto-generated from Sentry Project: {project_name}",
                    owner=admin_user
                )
                print(f"Auto-created PM Project: {project_name}")

        # --- Auto-Created Task Logic ---
        # Now that we know the project exists, let's create the Task if it doesn't exist
        try:
             pm_project = Project.objects.get(name=project_name)
             if not Task.objects.filter(sentry_error_id=instance.id).exists():
                 # Fetch default TO_DO status for the project
                 from .models import TaskStatus
                 status = TaskStatus.objects.filter(project=pm_project, category='TO_DO').first()
                 if not status:
                     status = TaskStatus.objects.filter(project=pm_project).first()

                 # Default logic: Assign to project owner or leave unassigned
                 task = Task.objects.create(
                     project=pm_project,
                     title=f"Fix: {instance.title}",
                     description=f"Auto-generated task for Issue ID: {instance.id}\nHash: {instance.hash_id}",
                     status=status,
                     priority='HIGH',
                     sentry_error_id=instance.id,
                 )
                 print(f"Auto-created PM Task for Issue: {instance.id}")
        except Project.DoesNotExist:
             print(f"Could not find PM Project {project_name} to create task.")

@receiver(post_delete, sender=Issue)
def delete_task_with_issue(sender, instance, **kwargs):
    """
    When an Issue is deleted, delete the corresponding Task in Project Management.
    """
    Task.objects.filter(sentry_error_id=instance.id).delete()
    print(f"Auto-deleted PM Task for Issue: {instance.id}")

@receiver(post_delete, sender=Task)
def delete_issue_with_task(sender, instance, **kwargs):
    """
    When a Task is deleted, delete the corresponding Issue in Tracker if it exists.
    """
    if instance.sentry_error_id:
        try:
            Issue.objects.filter(id=instance.sentry_error_id).delete()
            print(f"Auto-deleted Issue {instance.sentry_error_id} because Task {instance.id} was deleted.")
        except Exception as e:
            print(f"Error deleting issue {instance.sentry_error_id}: {e}")

@receiver(post_save, sender=Task)
def sync_issue_status_with_task(sender, instance, **kwargs):
    """
    Synchronize Issue status based on Task status:
    DONE/APPROVED -> resolved
    Others -> open
    """
    if instance.sentry_error_id:
        try:
            issue = Issue.objects.get(id=instance.sentry_error_id)
            
            if instance.status.category == 'DONE':
                if issue.status != 'resolved':
                    issue.status = 'resolved'
                    # Set resolver to the assignee if available
                    if instance.assigned_to:
                        issue.resolved_by = instance.assigned_to
                    issue.save()
            else:
                if issue.status != 'open':
                    issue.status = 'open'
                    issue.resolved_by = None
                    issue.save()
        except Issue.DoesNotExist:
            pass

# ─── System Technical Design New Signals ──────────────────────────────────────

from .automation_engine import AutomationEngine
from .plugin_manager import PluginManager

@receiver(post_save, sender=Task)
def trigger_automation_and_plugins(sender, instance, created, **kwargs):
    """
    Trigger Automation Engine and Plugin Hooks on Task changes.
    """
    if created:
        event_type = 'TASK_CREATED'
        PluginManager.call_hooks('post_task_create', task=instance)
    else:
        event_type = 'TASK_UPDATED'
        PluginManager.call_hooks('post_task_update', task=instance)
        
    # Trigger automation rules based on the event
    AutomationEngine.process_event(event_type, instance.project_id, task=instance)
