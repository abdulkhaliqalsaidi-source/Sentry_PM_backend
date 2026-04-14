import importlib
import logging
from .models import PluginModel

logger = logging.getLogger(__name__)

class PluginManager:
    _hooks = {
        'post_task_create': [],
        'post_task_update': [],
        'post_status_change': []
    }

    @classmethod
    def initialize_plugins(cls):
        # Clear hooks before re-initializing
        for key in cls._hooks:
            cls._hooks[key] = []
            
        plugins = PluginModel.objects.filter(enabled=True)
        for plugin in plugins:
            try:
                module = importlib.import_module(plugin.entry_point)
                if hasattr(module, 'register'):
                    module.register(cls)
                logger.info(f"Loaded plugin: {plugin.name}")
            except Exception as e:
                logger.error(f"Failed to load plugin {plugin.name}: {e}")

    @classmethod
    def register_hook(cls, hook_name, func):
        if hook_name in cls._hooks:
            cls._hooks[hook_name].append(func)

    @classmethod
    def call_hooks(cls, hook_name, *args, **kwargs):
        if hook_name in cls._hooks:
            for func in cls._hooks[hook_name]:
                try:
                    func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in hook {hook_name}: {e}")
