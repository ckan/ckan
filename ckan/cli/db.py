# encoding: utf-8

import inspect
import logging
import os
import contextlib

import click
from itertools import groupby

import ckan.migration as migration_repo
import ckan.plugins as p
import ckan.plugins.toolkit as tk
import ckan.model as model
from ckan.common import config

log = logging.getLogger(__name__)

applies_to_plugin = click.option("-p", "--plugin", help="Affected plugin.")


@click.group(short_help="Database management commands.")
def db():
    """Database management commands.
    """
    pass


@db.command()
def init():
    """Initialize the database.
    """
    log.info("Initialize the Database")
    try:
        model.repo.init_db()
    except Exception as e:
        tk.error_shout(e)
    else:
        click.secho('Initialising DB: SUCCESS', fg='green', bold=True)


PROMPT_MSG = 'This will delete all of your data!\nDo you want to continue?'


@db.command()
@click.confirmation_option(prompt=PROMPT_MSG)
def clean():
    """Clean the database.
    """
    try:
        model.repo.clean_db()
    except Exception as e:
        tk.error_shout(e)
    else:
        click.secho('Cleaning DB: SUCCESS', fg='green', bold=True)


@db.command()
@click.option('-v', '--version', help='Migration version', default='head')
@applies_to_plugin
def upgrade(version, plugin):
    """Upgrade the database.
    """
    _run_migrations(plugin, version)
    click.secho('Upgrading DB: SUCCESS', fg='green', bold=True)


@db.command()
@click.option('-v', '--version', help='Migration version', default='base')
@applies_to_plugin
def downgrade(version, plugin):
    """Downgrade the database.
    """
    _run_migrations(plugin, version, False)
    click.secho('Downgrading DB: SUCCESS', fg='green', bold=True)


@db.command()
@click.option("--apply", is_flag=True, help="Apply all pending migrations")
def pending_migrations(apply):
    """List all sources with unapplied migrations.
    """
    pending = _get_pending_plugins()
    if not pending:
        click.secho("All plugins are up-to-date", fg="green")
    for plugin, n in sorted(pending.items()):
        click.secho("{n} unapplied migrations for {p}".format(
            p=click.style(plugin, bold=True),
            n=click.style(str(n), bold=True)))
        if apply:
            _run_migrations(plugin)


def _get_pending_plugins():
    from alembic.command import history
    plugins = [(plugin, state)
               for plugin, state
               in ((plugin, current_revision(plugin))
                   for plugin in config['ckan.plugins'].split())
               if state and not state.endswith('(head)')]
    pending = {}
    for plugin, current in plugins:
        with _repo_for_plugin(plugin) as repo:
            repo.setup_migration_version_control()
            history(repo.alembic_config)
            ahead = repo.take_alembic_output()
            if current != 'base':
                # The last revision in history describes step from void to the
                # first revision. If we not on the `base`, we've already run
                # this migration
                ahead = ahead[:-1]
            if ahead:
                pending[plugin] = len(ahead)
    return pending


def _run_migrations(plugin, version="head", forward=True):
    if not version:
        version = "head" if forward else "base"
    with _repo_for_plugin(plugin) as repo:
        if forward:
            repo.upgrade_db(version)
        else:
            repo.downgrade_db(version)


@db.command()
@applies_to_plugin
def version(plugin):
    """Returns current version of data schema.
    """
    current = current_revision(plugin)
    try:
        current = _version_hash_to_ordinal(current)
    except ValueError:
        pass
    click.secho('Current DB version: {}'.format(current),
                fg='green',
                bold=True)


def current_revision(plugin):
    with _repo_for_plugin(plugin) as repo:
        repo.setup_migration_version_control()
        return repo.current_version()


@db.command("duplicate_emails", short_help="Check users email for duplicate")
def duplicate_emails():
    '''Check users email for duplicate'''
    log.info("Searching for accounts with duplicate emails.")

    q = model.Session.query(model.User.email,
                            model.User.name) \
        .filter(model.User.state == "active") \
        .filter(model.User.email != "") \
        .order_by(model.User.email).all()

    duplicates_found = False
    try:
        for k, grp in groupby(q, lambda x: x[0]):
            users = [user[1] for user in grp]
            if len(users) > 1:
                duplicates_found = True
                s = "{} appears {} time(s). Users: {}"
                click.secho(
                    s.format(k, len(users), ", ".join(users)),
                    fg="green", bold=True)
    except Exception as e:
        tk.error_shout(e)
    if not duplicates_found:
        click.secho("No duplicate emails found", fg="green")


def _version_hash_to_ordinal(version):
    if 'base' == version:
        return 0
    versions_dir = os.path.join(os.path.dirname(migration_repo.__file__),
                                'versions')
    versions = sorted(os.listdir(versions_dir))

    # latest version looks like `123abc (head)`
    if version.endswith('(head)'):
        return int(versions[-1].split('_')[0])
    for name in versions:
        if version in name:
            return int(name.split('_')[0])
    tk.error_shout('Version `{}` was not found in {}'.format(
        version, versions_dir))


def _resolve_alembic_config(plugin):
    if plugin:
        plugin_obj = p.get_plugin(plugin)
        if plugin_obj is None:
            tk.error_shout("Plugin '{}' cannot be loaded.".format(plugin))
            raise click.Abort()
        plugin_dir = os.path.dirname(inspect.getsourcefile(type(plugin_obj)))

        # if there is `plugin` folder instead of single_file, find
        # plugin's parent dir
        ckanext_idx = plugin_dir.rfind("/ckanext/") + 9
        idx = plugin_dir.find("/", ckanext_idx)
        if ~idx:
            plugin_dir = plugin_dir[:idx]
        migration_dir = os.path.join(plugin_dir, "migration", plugin)
    else:
        import ckan.migration as _cm
        migration_dir = os.path.dirname(_cm.__file__)
    return os.path.join(migration_dir, "alembic.ini")


@contextlib.contextmanager
def _repo_for_plugin(plugin):
    original = model.repo._alembic_ini
    model.repo._alembic_ini = _resolve_alembic_config(plugin)
    try:
        yield model.repo
    finally:
        model.repo._alembic_ini = original
