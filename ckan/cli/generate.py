# encoding: utf-8

from __future__ import print_function
import os

import alembic.command
import click
from alembic.config import Config as AlembicConfig

import ckan
from ckan.cli.db import _resolve_alembic_config
import ckan.plugins.toolkit as tk

import uuid
import string
import secrets
from ckan.cli import error_shout


class CKANAlembicConfig(AlembicConfig):
    def get_template_directory(self):
        return os.path.join(os.path.dirname(ckan.__file__),
                            u"../contrib/alembic")


@click.group()
def generate():
    """Scaffolding for regular development tasks.
    """
    pass


@generate.command(name=u'extension', short_help=u"Create empty extension.")
@click.option(u'-o',
              u'--output-dir',
              help=u"Location to put the generated "
              u"template.",
              default=u'.')
def extension(output_dir):
    """Generate empty extension files to expand CKAN.
    """
    try:
        from cookiecutter.main import cookiecutter
    except ImportError:
        tk.error_shout(u"`cookiecutter` library is missing from import path.")
        tk.error_shout(u"Make sure you have dev-dependencies installed:")
        tk.error_shout(u"\tpip install -r dev-requirements.txt")
        raise click.Abort()

    cur_loc = os.path.dirname(os.path.abspath(__file__))
    os.chdir(cur_loc)
    os.chdir(u'../../contrib/cookiecutter/ckan_extension/')
    template_loc = os.getcwd()

    # Prompt user for information
    click.echo(u"\n")
    while True:
        name = click.prompt(u"Extension's name",
                            default=u"must begin 'ckanext-'")
        if not name.startswith(u"ckanext-"):
            print(u"ERROR: Project name must start with 'ckanext-' > {}\n"
                  .format(name))
        else:
            break

    author = click.prompt(u"Author's name", default=u"")
    email = click.prompt(u"Author's email", default=u"")
    github = click.prompt(u"Your Github user or organization name",
                          default=u"")
    description = click.prompt(u"Brief description of the project",
                               default=u"")
    keywords = click.prompt(u"List of keywords (separated by spaces)",
                            default=u"CKAN")

    # Ensure one instance of 'CKAN' in keywords
    keywords = [u"CKAN"] + [
        k for k in keywords.strip().split() if k.lower() != u"ckan"
    ]
    keywords = u' '.join(keywords)

    # Set short name and plugin class name
    project_short = name[8:].lower().replace(u'-', u'_')
    plugin_class_name = project_short.title().replace(u'_', u'') + u'Plugin'

    context = {
        u"project": name,
        u"description": description,
        u"author": author,
        u"author_email": email,
        u"keywords": keywords,
        u"github_user_name": github,
        u"project_shortname": project_short,
        u"plugin_class_name": plugin_class_name,
        u"_source": u"cli"
    }

    if output_dir == u'.':
        os.chdir(u'../../../..')
        output_dir = os.getcwd()

    cookiecutter(template_loc, no_input=True, extra_context=context,
                 output_dir=output_dir)

    print(u"\nWritten: {}/{}".format(output_dir, name))


@generate.command(name=u'config',
                  short_help=u'Create a ckan.ini file.')
@click.argument(u'output_path', nargs=1)
def make_config(output_path):
    u"""Generate a new CKAN configuration ini file."""

    # Output to current directory if no path is specified
    if u'/' not in output_path:
        output_path = os.path.join(os.getcwd(), output_path)

    cur_loc = os.path.dirname(os.path.abspath(__file__))
    template_loc = os.path.join(cur_loc, u'..', u'config',
                                u'deployment.ini_tmpl')
    template_variables = {
        u'app_instance_uuid': uuid.uuid4(),
        u'app_instance_secret': secrets.token_urlsafe(20)[:25]
    }

    with open(template_loc, u'r') as file_in:
        template = string.Template(file_in.read())

        try:
            with open(output_path, u'w') as file_out:
                file_out.writelines(template.substitute(template_variables))

        except IOError as e:
            error_shout(e)
            raise click.Abort()


@generate.command()
@click.option(u"-p",
              u"--plugin",
              help=(u"Plugin's that requires migration"
                    u"(name, used in `ckan.plugins` config section). "
                    u"If not provided, core CKAN migration created instead."))
@click.option(u"-m",
              u"--message",
              help=u"Message string to use with `revision`.")
def migration(plugin, message):
    """Create new alembic revision for DB migration.
    """
    import ckan.model
    if not tk.config:
        tk.error_shout(u'Config is not loaded')
        raise click.Abort()
    config = CKANAlembicConfig(_resolve_alembic_config(plugin))
    migration_dir = os.path.dirname(config.config_file_name)
    config.set_main_option(u"sqlalchemy.url",
                           str(ckan.model.repo.metadata.bind.url))
    config.set_main_option(u'script_location', migration_dir)

    if not os.path.exists(os.path.join(migration_dir, u'script.py.mako')):
        alembic.command.init(config, migration_dir)

    rev = alembic.command.revision(config, message)
    click.secho(
        u"Revision file created. Now, you need to update it: \n\t{}".format(
            rev.path),
        fg=u"green")
