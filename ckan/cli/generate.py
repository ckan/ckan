# encoding: utf-8

from __future__ import print_function
import contextlib
import os
import shutil

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
                            "../contrib/alembic")


@click.group(short_help="Scaffolding for regular development tasks.")
def generate():
    """Scaffolding for regular development tasks.
    """
    pass


@generate.command(name='extension', short_help="Create empty extension.")
@click.option('-o',
              '--output-dir',
              help="Location to put the generated "
              "template.",
              default='.')
def extension(output_dir):
    """Generate empty extension files to expand CKAN.
    """
    try:
        from cookiecutter.main import cookiecutter
    except ImportError:
        tk.error_shout("`cookiecutter` library is missing from import path.")
        tk.error_shout("Make sure you have dev-dependencies installed:")
        tk.error_shout("\tpip install -r dev-requirements.txt")
        raise click.Abort()

    cur_loc = os.path.dirname(os.path.abspath(__file__))
    os.chdir(cur_loc)
    os.chdir('../../contrib/cookiecutter/ckan_extension/')
    template_loc = os.getcwd()

    # Prompt user for information
    click.echo("\n")
    while True:
        name = click.prompt("Extension's name",
                            default="must begin 'ckanext-'")
        if not name.startswith("ckanext-"):
            print("ERROR: Project name must start with 'ckanext-' > {}\n"
                  .format(name))
        else:
            break

    author = click.prompt("Author's name", default="")
    email = click.prompt("Author's email", default="")
    github = click.prompt("Your Github user or organization name",
                          default="")
    description = click.prompt("Brief description of the project",
                               default="")
    keywords = click.prompt("List of keywords (separated by spaces)",
                            default="CKAN")

    # Ensure one instance of 'CKAN' in keywords
    keywords = ["CKAN"] + [
        k for k in keywords.strip().split() if k.lower() != "ckan"
    ]
    keywords = ' '.join(keywords)

    # Set short name and plugin class name
    project_short = name[8:].lower().replace('-', '_')
    plugin_class_name = project_short.title().replace('_', '') + 'Plugin'

    include_examples = int(click.confirm(
        "Do you want to include code examples?"))
    context = {
        "project": name,
        "description": description,
        "author": author,
        "author_email": email,
        "keywords": keywords,
        "github_user_name": github,
        "project_shortname": project_short,
        "plugin_class_name": plugin_class_name,
        "include_examples": include_examples,
        "_source": "cli",
    }

    if output_dir == '.':
        os.chdir('../../../..')
        output_dir = os.getcwd()

    cookiecutter(template_loc, no_input=True, extra_context=context,
                 output_dir=output_dir)

    if not include_examples:
        remove_code_examples(
            os.path.join(
                output_dir, context["project"], "ckanext", project_short))

    print("\nWritten: {}/{}".format(output_dir, name))


_code_examples = [
    "cli.py",
    "helpers.py",
    "logic",
    "views.py",
    "tests/logic",
    "tests/test_helpers.py",
    "tests/test_views.py",
]


def remove_code_examples(root: str):
    """Remove example files from extension's template.
    """
    for item in _code_examples:
        path = os.path.join(root, item)
        with contextlib.suppress(FileNotFoundError):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)


@generate.command(name='config',
                  short_help='Create a ckan.ini file.')
@click.argument('output_path', nargs=1)
def make_config(output_path):
    """Generate a new CKAN configuration ini file."""

    # Output to current directory if no path is specified
    if '/' not in output_path:
        output_path = os.path.join(os.getcwd(), output_path)

    cur_loc = os.path.dirname(os.path.abspath(__file__))
    template_loc = os.path.join(cur_loc, '..', 'config',
                                'deployment.ini_tmpl')
    template_variables = {
        'app_instance_uuid': uuid.uuid4(),
        'app_instance_secret': secrets.token_urlsafe(20)[:25]
    }

    with open(template_loc, 'r') as file_in:
        template = string.Template(file_in.read())

        try:
            with open(output_path, 'w') as file_out:
                file_out.writelines(template.substitute(template_variables))

        except IOError as e:
            error_shout(e)
            raise click.Abort()


@generate.command()
@click.option("-p",
              "--plugin",
              help=("Plugin's that requires migration"
                    "(name, used in `ckan.plugins` config section). "
                    "If not provided, core CKAN migration created instead."))
@click.option("-m",
              "--message",
              help="Message string to use with `revision`.")
def migration(plugin, message):
    """Create new alembic revision for DB migration.
    """
    import ckan.model
    if not tk.config:
        tk.error_shout('Config is not loaded')
        raise click.Abort()
    config = CKANAlembicConfig(_resolve_alembic_config(plugin))
    migration_dir = os.path.dirname(config.config_file_name)
    config.set_main_option("sqlalchemy.url",
                           str(ckan.model.repo.metadata.bind.url))
    config.set_main_option('script_location', migration_dir)

    if not os.path.exists(os.path.join(migration_dir, 'script.py.mako')):
        alembic.command.init(config, migration_dir)

    rev = alembic.command.revision(config, message)
    click.secho(
        "Revision file created. Now, you need to update it: \n\t{}".format(
            rev.path),
        fg="green")
