from django.apps import AppConfig


class ProjectManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'project_management'

    def ready(self):
        import project_management.signals
        # Load plugins after all models are ready
        try:
            from plugins import load_plugins
            load_plugins()
        except Exception:
            pass  # DB may not be ready during migrations
