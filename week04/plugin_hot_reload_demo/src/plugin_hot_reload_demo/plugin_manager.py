"""Plugin discovery and reload helpers."""

from __future__ import annotations

import importlib
import pkgutil
import sys
from types import ModuleType

from .models import PluginSpec


class PluginManager:
    """Load and reload plugins from a package."""

    def __init__(self, package_name: str):
        self.package_name = package_name
        self._modules: dict[str, ModuleType] = {}
        self._plugins: list[PluginSpec] = []
        self.reload_plugins()

    def reload_plugins(self) -> list[PluginSpec]:
        """Reload all plugin modules and rebuild the plugin registry."""

        package = importlib.import_module(self.package_name)
        plugins: list[PluginSpec] = []
        modules: dict[str, ModuleType] = {}

        for module_info in pkgutil.iter_modules(package.__path__):
            module_name = f"{self.package_name}.{module_info.name}"
            if module_name in self._modules:
                module = importlib.reload(self._modules[module_name])
            elif module_name in sys.modules:
                module = importlib.reload(sys.modules[module_name])
            else:
                module = importlib.import_module(module_name)
            modules[module_name] = module
            plugins.append(module.PLUGIN)

        self._modules = modules
        self._plugins = plugins
        return self._plugins

    def get_plugins(self) -> list[PluginSpec]:
        """Return currently loaded plugins."""

        return list(self._plugins)
