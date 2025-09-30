from __future__ import annotations

import os
import ckan.plugins as p

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def collect_themes():
    """Collect available themes from core and plugins."""
    themes = {
        "classic": {"path": os.path.join(root, "templates")},
        "midnight-blue": {"path": os.path.join(root, "templates-midnight-blue")},
    }
    for plugin in p.PluginImplementations(p.ITheme):
        themes.update(plugin.register_themes())

    return themes


def resolve_paths(theme: str | None) -> list[str]:
    """Resolve theme paths including parent themes."""

    themes = collect_themes()
    paths = []
    while theme:
        info = themes[theme]
        paths.append(info["path"])
        theme = info.get("extends", None)

    return paths[::-1]
