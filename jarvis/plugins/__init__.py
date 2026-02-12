import importlib
import inspect
import logging
import pkgutil
from types import ModuleType
from typing import List

from jarvis.plugins.base import Plugin

logger = logging.getLogger(__name__)


SAFE_PLUGIN_PREFIX = f"{__name__}."
SAFE_MODULE_SUFFIX = "_plugin"


def _is_safe_module_name(name: str) -> bool:
    return name.endswith(SAFE_MODULE_SUFFIX) and name.replace("_", "").isalnum()


def _validate_plugin_class(module: ModuleType, obj: type) -> bool:
    if not issubclass(obj, Plugin) or obj is Plugin:
        return False
    if obj.__module__ != module.__name__:
        return False
    name = getattr(obj, "name", "")
    trigger = getattr(obj, "trigger", "")
    execute = getattr(obj, "execute", None)
    return isinstance(name, str) and bool(name.strip()) and isinstance(trigger, str) and bool(trigger.strip()) and callable(execute)


def load_plugins() -> List[Plugin]:
    plugins: List[Plugin] = []

    for module_info in pkgutil.iter_modules(__path__):
        if module_info.name in {"base", "__init__"}:
            continue
        if not _is_safe_module_name(module_info.name):
            logger.warning("Skipping unsafe plugin module name: %s", module_info.name)
            continue

        module_name = f"{__name__}.{module_info.name}"
        if not module_name.startswith(SAFE_PLUGIN_PREFIX):
            logger.warning("Skipping out-of-scope plugin module: %s", module_name)
            continue

        try:
            module = importlib.import_module(module_name)
        except Exception:
            logger.exception("Failed to import plugin module %s", module_name)
            continue

        for _, obj in inspect.getmembers(module, inspect.isclass):
            if not _validate_plugin_class(module, obj):
                continue
            try:
                plugins.append(obj())
            except Exception:
                logger.exception("Failed to initialize plugin class %s", obj.__name__)

    return plugins
