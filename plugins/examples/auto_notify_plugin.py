"""
Auto Notify Plugin - sends in-app notifications on key events.
Entry point: plugins.examples.auto_notify_plugin
"""
import logging
from plugins.base import BasePlugin

logger = logging.getLogger("plugin.auto_notify")


class Plugin(BasePlugin):
    name = "auto-notify-plugin"
    version = "1.0.0"
    description = "Sends in-app notifications when tasks are overdue or high-priority tasks are created."

    def setup(self):
        logger.info("[AutoNotifyPlugin] Initialized.")

    def on_task_created(self, task):
        """Notify project members when a HIGH priority task is created."""
        if task.priority != 'HIGH':
            return
        try:
            from project_management.models import ProjectRole, Notification
            members = ProjectRole.objects.filter(project=task.project).select_related('user')
            actor = task.reporter or task.project.owner
            for role in members:
                if role.user != actor:
                    Notification.objects.create(
                        recipient=role.user,
                        actor=actor,
                        verb="أنشأ مهمة عالية الأولوية",
                        type="SYSTEM",
                        task=task,
                        project=task.project,
                    )
        except Exception as e:
            logger.error(f"[AutoNotifyPlugin] on_task_created error: {e}")

    def on_task_status_changed(self, task, old_status, new_status):
        """Notify assignee when their task moves to DONE."""
        if new_status != 'DONE' or not task.assigned_to:
            return
        try:
            from project_management.models import Notification
            Notification.objects.create(
                recipient=task.assigned_to,
                actor=task.assigned_to,
                verb="أكملت المهمة",
                type="STATUS_CHANGE",
                task=task,
                project=task.project,
            )
        except Exception as e:
            logger.error(f"[AutoNotifyPlugin] on_task_status_changed error: {e}")
