# encoding: utf-8

from __future__ import print_function
import os
import sys
import click
import uuid
import string
import secrets
from ckan.cli import error_shout


@click.group(
    name=u'generate',
    short_help=u"Generate empty extension files to expand CKAN.",
    invoke_without_command=True,
)
def generate():
    try:
        from cookiecutter.main import cookiecutter
    except ImportError:
        error_shout(u"`cookiecutter` library is missing from import path.")
        error_shout(u"Make sure you have dev-dependencies installed:")
        error_shout(u"\tpip install -r dev-requirements.txt")
        raise click.Abort()


@generate.command(name=u'extension', short_help=u"Create empty extension.")
@click.option(u'-o', u'--output-dir', help=u"Location to put the generated "
                                           u"template.",
              default=u'.')
def extension(output_dir):
    from cookiecutter.main import cookiecutter
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
    keywords = keywords.strip().split()
    keywords = [keyword for keyword in keywords
                if keyword not in (u'ckan', u'CKAN')]
    keywords.insert(0, u'CKAN')
    keywords = u' '.join(keywords)

    # Set short name and plugin class name
    project_short = name[8:].lower().replace(u'-', u'_')
    plugin_class_name = project_short.title().replace(u'_', u'') + u'Plugin'

    context = {u"project": name,
               u"description": description,
               u"author": author,
               u"author_email": email,
               u"keywords": keywords,
               u"github_user_name": github,
               u"project_shortname": project_short,
               u"plugin_class_name": plugin_class_name,
               u"_source": u"cli"}

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
            sys.exit(1)
