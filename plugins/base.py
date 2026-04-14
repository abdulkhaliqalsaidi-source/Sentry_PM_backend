"""
BasePlugin - all plugins should inherit from this class.
Override only the hooks you need.
"""


class BasePlugin:
    name: str = "unnamed"
    version: str = "1.0.0"
    description: str = ""

    # ── Lifecycle ──────────────────────────────────────────────────
    def setup(self):
        """Called once when the plugin is loaded."""
        pass

    def teardown(self):
        """Called when the plugin is unloaded/disabled."""
        pass

    # ── Task hooks ─────────────────────────────────────────────────
    def on_task_created(self, task):
        """Fired after a task is created. task = Task instance."""
        pass

    def on_task_updated(self, task):
        """Fired after a task is updated."""
        pass

    def on_task_status_changed(self, task, old_status, new_status):
        """Fired when a task's status changes."""
        pass

    def on_task_assigned(self, task, assignee):
        """Fired when a task is assigned to a user."""
        pass

    # ── Doc hooks ──────────────────────────────────────────────────
    def on_doc_created(self, doc):
        """Fired after a documentation page is created."""
        pass

    def on_doc_updated(self, doc):
        """Fired after a documentation page is updated."""
        pass

    # ── Comment hooks ──────────────────────────────────────────────
    def on_comment_added(self, comment):
        """Fired after a comment is added to a task."""
        pass

    # ── Sprint hooks ───────────────────────────────────────────────
    def on_sprint_started(self, sprint):
        """Fired when a sprint starts."""
        pass

    def on_sprint_completed(self, sprint):
        """Fired when a sprint is completed."""
        pass

    # ── HTTP endpoint (optional) ───────────────────────────────────
    def get_urls(self):
        """
        Return a list of Django URL patterns to register under
        /api/plugins/<plugin_name>/...
        Example:
            from django.urls import path
            return [path('status/', self.status_view)]
        """
        return []

    # ── Dashboard widget (optional) ───────────────────────────────
    def get_widget_data(self, project_id: int) -> dict:
        """
        Return JSON-serializable data for a frontend widget.
        Return None to skip.
        """
        return None
