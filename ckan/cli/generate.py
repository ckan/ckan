# encoding: utf-8

import os

import alembic.command
import click
from alembic.config import Config as AlembicConfig

import ckan
from ckan.cli.db import _resolve_alembic_config
import ckan.plugins.toolkit as tk

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
    name = click.prompt(
        u"Extenion's name (`ckanext-` prefix added automatically if not provided)"
    )
    if not name.startswith(u"ckanext-"):
        name = u"ckanext-" + name

    author = click.prompt(u"Author's name", default=u"")
    email = click.prompt(u"Author's email", default=u"")
    github = click.prompt(u"Your Github user or organization name",
                          default=u"")
    description = click.prompt(u"Brief description of the project",
                               default=u"")
    keywords = click.prompt(u"List of keywords (seperated by spaces)",
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

    cookiecutter(template_loc,
                 no_input=True,
                 extra_context=context,
                 output_dir=output_dir)


@generate.command()
@click.option(
    u"-p",
    u"--plugin",
    help=
    u"Plugin's that requires migration(name, used in `ckan.plugins` config section). If not provided, core CKAN migration created instead."
)
@click.option(u"-m",
              u"--message",
              help=u"Message string to use with `revision`.")
def migration(plugin, message):
    """Create new alembic revision for DB migration.
    """
    import ckan.model
    config = CKANAlembicConfig(_resolve_alembic_config(plugin))
    config.set_main_option("sqlalchemy.url",
                           str(ckan.model.repo.metadata.bind.url))

    migration_dir = os.path.dirname(config.config_file_name)
    if not os.path.isdir(migration_dir):
        alembic.command.init(config, migration_dir)
    rev = alembic.command.revision(config, message)
    click.secho(
        u"Revision file created. Now, you need to update it: \n\t{}".format(
            rev.path),
        fg=u"green")
