"""Small plugin registry compatible with the public RDFLib shape."""

from __future__ import annotations

from dataclasses import dataclass

from .exceptions import PluginException


@dataclass(frozen=True)
class Plugin:
    name: str
    kind: type
    module_path: str | None = None
    class_name: str | None = None
    implementation: type | None = None

    def getClass(self):
        if self.implementation is not None:
            return self.implementation
        if self.module_path is None or self.class_name is None:
            return self.kind
        from importlib import import_module
        return getattr(import_module(self.module_path), self.class_name)


_registry: dict[tuple[str, type], Plugin] = {}


def register(name, kind, module_path=None, class_name=None):
    if not isinstance(name, str) or not name:
        raise PluginException("plugin name must be a non-empty string")
    implementation = module_path if isinstance(module_path, type) else None
    plugin = Plugin(name, kind, None if implementation else module_path, class_name, implementation)
    _registry[(name, kind)] = plugin
    return plugin


def get(name, kind):
    try:
        return _registry[(name, kind)]
    except KeyError as error:
        raise PluginException(f"No plugin registered for {name!r}") from error


def plugins(kind=None):
    values = _registry.values()
    return iter(plugin for plugin in values if kind is None or plugin.kind is kind)
