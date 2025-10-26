"""Theme and UI classes for CKAN theming system.

A theme is a directory containing templates and static files, and
optionally extending a parent theme. A UI provides access to a set of
functions that can be used in templates for building the user interface.

Themes can be registered by CKAN plugins using the ITheme interface.

Example usage::

    theme = get_theme(config["ckan.ui.theme"])
    ui = theme.build_ui(app)
    btn = ui.button("Click me!", href="https://ckan.org")
"""

from __future__ import annotations

import abc
import os

from collections.abc import Iterable

from typing_extensions import override
from jinja2 import Environment

import ckan.plugins as p
from ckan import types
from ckan.common import config


root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Theme:
    """Information about a theme.

    :param path: Path to the theme directory.
    :param extends: Name of the parent theme, or None.
    """

    path: str
    extends: str | None

    def __init__(self, path: str, extends: str | None = None):
        self.path = path
        self.extends = extends

    def build_ui(self, app: types.CKANApp) -> UI:
        """Build a UI instance for this theme.

        The default implementation returns a MacroUI instance that loads
        macros from "macros/ui.html" in the theme's template directory.

        :param app: The CKAN application instance.
        :return: A UI instance.
        """
        return MacroUI(app.jinja_env)


class UI(Iterable[str], abc.ABC):
    """Abstract base class for theme UIs.

    A UI provides access to a set of macros that can be used in templates.
    """

    @override
    @abc.abstractmethod
    def __iter__(self) -> Iterable[str]:
        """Return an iterable of macro names provided by this UI."""


class MacroUI(UI):
    """A UI implementation that loads macros from a Jinja2 template.

    :param env: The Jinja2 environment to load templates from.
    """

    source: str = "macros/ui.html"

    def __init__(self, env: Environment):
        self.__env = env
        self.__tpl = env.get_template(self.source)

    def __getattr__(self, name: str):
        """Get a macro by name."""
        if config["debug"]:
            tpl = self.__env.get_template(self.source)
            mod = tpl.make_module()
        else:
            mod = self.__tpl.module
        return getattr(mod, name)

    @override
    def __iter__(self) -> Iterable[str]:
        for name in dir(self.__tpl.module):
            if name.startswith("_"):
                continue
            getattr(self.__tpl.module, name)
            yield name


def get_theme(name: str):
    """Get theme by name, raises KeyError if not found."""
    themes = collect_themes()
    return themes[name]


def collect_themes():
    """Collect available themes from core and plugins."""
    themes = {
        "classic": Theme(os.path.join(root, "templates")),
        "midnight-blue": Theme(os.path.join(root, "templates-midnight-blue")),
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
