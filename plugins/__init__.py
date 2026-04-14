"""
Plugin Engine - loads and manages enabled plugins from the database.
"""
import importlib
import logging

logger = logging.getLogger(__name__)

_loaded_plugins: dict = {}  # name -> plugin instance


def load_plugins():
    """Load all enabled plugins from DB. Call once at startup."""
    global _loaded_plugins
    _loaded_plugins = {}

    try:
        from project_management.models import PluginModel
        enabled = PluginModel.objects.filter(enabled=True)
        for record in enabled:
            _load_plugin(record)
    except Exception as e:
        logger.warning(f"[PluginEngine] Could not load plugins: {e}")


def _load_plugin(record):
    try:
        module = importlib.import_module(record.entry_point)
        plugin_class = getattr(module, 'Plugin', None)
        if plugin_class is None:
            logger.warning(f"[PluginEngine] {record.entry_point} has no 'Plugin' class")
            return
        instance = plugin_class()
        instance.setup()
        _loaded_plugins[record.name] = instance
        logger.info(f"[PluginEngine] Loaded plugin: {record.name}")
    except Exception as e:
        logger.error(f"[PluginEngine] Failed to load {record.entry_point}: {e}")


def reload_plugin(name: str):
    """Reload a single plugin by name."""
    try:
        from project_management.models import PluginModel
        record = PluginModel.objects.get(name=name)
        if record.enabled:
            _load_plugin(record)
        else:
            _loaded_plugins.pop(name, None)
    except Exception as e:
        logger.error(f"[PluginEngine] reload_plugin error: {e}")


def unload_plugin(name: str):
    plugin = _loaded_plugins.pop(name, None)
    if plugin:
        try:
            plugin.teardown()
        except Exception:
            pass


def fire(event: str, **kwargs):
    """Fire an event on all loaded plugins."""
    for name, plugin in list(_loaded_plugins.items()):
        handler = getattr(plugin, event, None)
        if callable(handler):
            try:
                handler(**kwargs)
            except Exception as e:
                logger.error(f"[PluginEngine] Plugin '{name}' error on '{event}': {e}")


def get_loaded() -> list:
    return list(_loaded_plugins.keys())
