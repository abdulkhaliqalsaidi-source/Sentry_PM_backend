"""
Logger Plugin - logs all task events to a file.
Entry point: plugins.examples.logger_plugin
"""
import logging
from plugins.base import BasePlugin

logger = logging.getLogger("plugin.logger")


class Plugin(BasePlugin):
    name = "logger-plugin"
    version = "1.0.0"
    description = "Logs all task and doc events to the Django logger."

    def setup(self):
        logger.info("[LoggerPlugin] Initialized.")

    def on_task_created(self, task):
        logger.info(f"[LoggerPlugin] Task created: '{task.title}' in project '{task.project.name}'")

    def on_task_updated(self, task):
        logger.info(f"[LoggerPlugin] Task updated: '{task.title}'")

    def on_task_status_changed(self, task, old_status, new_status):
        logger.info(f"[LoggerPlugin] Status changed: '{task.title}' {old_status} → {new_status}")

    def on_task_assigned(self, task, assignee):
        logger.info(f"[LoggerPlugin] Task '{task.title}' assigned to {assignee.username}")

    def on_doc_created(self, doc):
        logger.info(f"[LoggerPlugin] Doc created: '{doc.title}'")

    def on_sprint_completed(self, sprint):
        logger.info(f"[LoggerPlugin] Sprint completed: '{sprint.name}' — {sprint.completed_points} pts")
