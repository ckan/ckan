from __future__ import annotations


import abc
import os
from collections.abc import Iterable
from typing_extensions import override
from jinja2.runtime import Macro
import ckan.plugins as p
from ckan import types
from jinja2 import Environment

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Theme:
    path: str
    extends: str | None

    def __init__(self, path: str, extends: str | None = None):
        self.path = path
        self.extends = extends

    def build_ui(self, app: types.CKANApp) -> UI:
        return MacroUI(app.jinja_env)


class UI(Iterable[str], abc.ABC): ...


class MacroUI(UI):
    source: str = "macros/ui.html"

    def __init__(self, env: Environment):
        self.__env = env
        self.__tmpl = env.get_template(self.source)

    def __getattr__(self, name: str):
        return getattr(self.__tmpl.module, name)

    @override
    def __iter__(self) -> Iterable[str]:
        for name in dir(self.__tmpl.module):
            if name.startswith("_"):
                continue
            yield name


def get_theme(name: str):
    """Get theme by name, raises KeyError if not found."""
    themes = collect_themes()
    return themes[name]


def collect_themes():
    """Collect available themes from core and plugins."""
    themes = {
        "templates": Theme(os.path.join(root, "templates")),
        "templates-midnight-blue": Theme(os.path.join(root, "templates-midnight-blue")),
    }
    for plugin in p.PluginImplementations(p.ITheme):
        themes.update(plugin.register_themes())

    return themes


def resolve_paths(theme: str | None) -> list[str]:
    """Resolve theme paths including parent themes.

    :raises KeyError: if the parent theme is not found
    """

    themes = collect_themes()
    paths = []
    while theme:
        info = themes[theme]
        paths.append(info.path)
        theme = info.extends

    return paths[::-1]
