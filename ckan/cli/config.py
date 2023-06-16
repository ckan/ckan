# -*- coding: utf-8 -*-
from __future__ import annotations

import itertools
from typing import Iterable
import click

from ckan.config.declaration import Declaration, Flag
from ckan.config.declaration.key import Pattern
from ckan.common import config as cfg

from . import error_shout


@click.group(
    short_help="Search, validate and describe config options."
)
def config():
    pass


@config.command()
@click.argument("plugins", nargs=-1)
@click.option(
    "--core",
    is_flag=True,
    help="Include declarations of CKAN core config options",
)
@click.option(
    "--enabled",
    is_flag=True,
    help="Include declarations of plugins enabled in the CKAN config file",
)
@click.option(
    "-f",
    "--format",
    "fmt",
    type=click.Choice(["python", "yaml", "dict", "json", "toml"]),
    default="python",
    help="Output the config declaration in this format",
)
def describe(plugins: tuple[str, ...], core: bool, enabled: bool, fmt: str):
    """Print out config declarations for the given plugins."""
    decl = _declaration(plugins, core, enabled)
    if decl:
        click.echo(decl.describe(fmt))


@config.command()
@click.argument("plugins", nargs=-1)
@click.option(
    "--core",
    is_flag=True,
    help="Include declarations of CKAN core config options",
)
@click.option(
    "--enabled",
    is_flag=True,
    help="Include declarations of plugins enabled in the CKAN config file",
)
@click.option(
    "-d",
    "--include-docs",
    is_flag=True,
    help="Include documentation for options",
)
@click.option(
    "-m",
    "--minimal",
    is_flag=True,
    help="Print only options with the `required` flag enabled",
)
def declaration(
    plugins: tuple[str, ...],
    core: bool,
    enabled: bool,
    include_docs: bool,
    minimal: bool,
):
    """Print declared config options for the given plugins."""

    decl = _declaration(plugins, core, enabled)
    if decl:
        click.echo(decl.into_ini(minimal, include_docs))


@config.command()
@click.argument("pattern", default="*")
@click.option(
    "-i",
    "--include-plugin",
    "plugins",
    multiple=True,
    help="Include this plugin even if disabled",
)
@click.option(
    "--with-default",
    is_flag=True,
    help="Print default value of the config option",
)
@click.option(
    "--with-current",
    is_flag=True,
    help="Print an actual value of the config option",
)
@click.option(
    "--custom-only",
    is_flag=True,
    help="Ignore options that are using default value",
)
@click.option(
    "--no-custom",
    is_flag=True,
    help="Ignore options that are not using default value",
)
@click.option(
    "--explain", is_flag=True, help="Print documentation for config option"
)
def search(
    pattern: str,
    plugins: tuple[str, ...],
    with_default: bool,
    with_current: bool,
    custom_only: bool,
    no_custom: bool,
    explain: bool,
):
    """Print all declared config options that match pattern."""
    decl = _declaration(plugins, True, True)

    for key in decl.iter_options(pattern=pattern):
        if isinstance(key, Pattern):
            continue
        option = decl[key]
        default = option.default
        current = option.normalize(cfg.get(str(key), default))
        if no_custom and default != current:
            continue
        if custom_only and default == current:
            continue

        default_section = ""
        current_section = ""
        if with_default:
            default_section = click.style(
                f" [Default: {repr(default)}]", fg="red"
            )
        if with_current:
            current_section = click.style(
                f" [Current: {repr(current)}]", fg="green"
            )
        docs = ""
        if explain and option.description:
            lines = option.description.splitlines()
            lines += ["", f"Default value: {repr(default)}"]
            if option.example:
                lines += ["", f"Example: {key} = {option.example}"]
            docs = "\n".join(f"\t{dl}" for dl in lines)
            docs = click.style(f"\n{docs}\n", bold=True)

        line = f"{key}{default_section}{current_section}{docs}"
        click.secho(line)


@config.command()
@click.option(
    "-i",
    "--include-plugin",
    "plugins",
    multiple=True,
    help="Include this plugin even if disabled",
)
def undeclared(plugins: tuple[str, ...]):
    """Print config options that have no declaration.

    This command includes options from the config file as well as options set
    in run-time, by IConfigurer, for example.

    """
    decl = _declaration(plugins, True, True)

    declared = set(decl.iter_options(exclude=Flag.none()))
    patterns = {key for key in declared if isinstance(key, Pattern)}
    declared -= patterns
    available = set(cfg)

    undeclared = {
        s
        for s in available.difference(declared)
        if not any(s == p for p in patterns)
    }

    for key in undeclared:
        click.echo(key)


@config.command()
@click.option(
    "-i",
    "--include-plugin",
    "plugins",
    multiple=True,
    help="Include this plugin even if disabled",
)
def validate(plugins: tuple[str, ...]):
    """Validate the global configuration object against the declaration."""
    decl = _declaration(plugins, True, True)
    _, errors = decl.validate(cfg)

    for name, errors in errors.items():
        click.secho(name, bold=True)
        for error in errors:
            error_shout("\t" + error)


def _declaration(
    plugins: Iterable[str], include_core: bool, include_enabled: bool
) -> Declaration:
    decl = Declaration()
    if include_core:
        decl.load_core_declaration()

    additional = ()
    if include_enabled:
        additional = (
            p for p in cfg.get("ckan.plugins") if p not in plugins
        )

    for name in itertools.chain(additional, plugins):
        decl.load_plugin(name)

    return decl
