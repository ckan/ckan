# -*- coding: utf-8 -*-

import itertools
from typing import Iterable, Set, Tuple
import click

from ckan.config.declaration import Declaration, Flag
from ckan.config.declaration.key import Pattern
from ckan.common import config as cfg

from . import error_shout


@click.group(
    short_help="Search, validate and describe config options on strict mode")
def config():
    mode = cfg.get_value("config.mode")
    if mode != "strict":
        error_shout(
            "`config.mode = strict` is required to use the declarative"
            " config features")
        raise click.Abort()


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
def describe(plugins: Tuple[str, ...], core: bool, enabled: bool, fmt: str):
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
    "-q",
    "--no-comments",
    is_flag=True,
    help="Do not include comments",
)
@click.option(
    "-m",
    "--minimal",
    is_flag=True,
    help="Print only mandatory options",
)
def declaration(
    plugins: Tuple[str, ...],
    core: bool,
    enabled: bool,
    no_comments: bool,
    minimal: bool,
):
    """Print declared config options for the given plugins."""

    decl = _declaration(plugins, core, enabled)
    if decl:
        click.echo(decl.into_ini(minimal, no_comments))


@config.command()
@click.argument("pattern", default="*")
@click.option(
    "-i", "--include-plugin", "plugins", multiple=True,
    help="Include this plugin even if disabled")
@click.option("--with-default", is_flag=True)
@click.option("--with-current", is_flag=True)
@click.option("--custom-only", is_flag=True)
@click.option("--no-custom", is_flag=True)
def search(
    pattern: str,
    plugins: Tuple[str, ...],
    with_default: bool,
    with_current: bool,
    custom_only: bool,
    no_custom: bool,
):
    """Print all declared config options that match pattern."""
    decl = _declaration(plugins, True, True)

    for key in decl.iter_options(pattern=pattern):
        if isinstance(key, Pattern):
            continue
        option = decl[key]
        default = option.default
        current = option._normalize(cfg.get(key, default))
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

        line = f"{key}{default_section}{current_section}"
        click.secho(line)


@config.command()
@click.option(
    "-i", "--include-plugin", "plugins", multiple=True,
    help="Include this plugin even if disabled")
def undeclared(plugins: Tuple[str, ...]):
    """Print config options that have no declaration.

    This command includes options from the config file as well as options set
    in run-time, by IConfigurer, for example.

    """
    decl = _declaration(plugins, True, True)

    declared = set(decl.iter_options(exclude=Flag.none()))
    patterns = {key for key in declared if isinstance(key, Pattern)}
    declared -= patterns
    available: Set[str] = set(cfg)

    undeclared = {
        s
        for s in available.difference(declared)
        if not any(s == p for p in patterns)
    }

    for key in undeclared:
        click.echo(key)


@config.command()
@click.option(
    "-i", "--include-plugin", "plugins", multiple=True,
    help="Include this plugin even if disabled")
def validate(plugins: Tuple[str, ...]):
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
            p for p in cfg.get_value("ckan.plugins") if p not in plugins
        )

    for name in itertools.chain(additional, plugins):
        decl.load_plugin(name)

    return decl
