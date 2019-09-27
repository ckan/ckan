# encoding: utf-8

import os
import click
from ckan.cli import error_shout
from cookiecutter.main import cookiecutter


@click.group(name=u'generate',
             short_help=u"Generate empty extension files to expand CKAN.")
def generate():
    pass


@generate.command(name=u'extension', short_help=u"Create empty extension.")
@click.option(u'-n', u'--name', help=u"Name of the extension (must begin "
                                     u"with 'ckanext-')",
                                     default="extension")
@click.option(u'-o', u'--output-dir', help=u"Location to put the generated "
                                           u"template.",
                                           default='.')
def extension(name, output_dir):
    cur_loc = os.path.dirname(os.path.abspath(__file__))
    os.chdir(cur_loc)
    os.chdir('../../contrib/cookiecutter/ckan_extension/')
    template_loc = os.getcwd()

    # Prompt user for information
    click.echo("\n")
    author = click.prompt("Author's name", default="")
    email = click.prompt("Author's email", default="")
    github = click.prompt("Your Github user or organization name", default="")
    description = click.prompt("Brief description of the project",
        default="")
    keywords = click.prompt("List of keywords (seperated by spaces)",
        default="CKAN")

    # Ensure one instance of 'CKAN' in keywords
    keywords = keywords.strip().split()
    keywords = [keyword for keyword in keywords
                if keyword not in ('ckan', 'CKAN')]
    keywords.insert(0, 'CKAN')
    keywords = u' '.join(keywords)

    # Set short name and plugin class name
    project_shortname = name[8:].lower().replace('-', '_')
    plugin_class_name = project_shortname.title().replace('_','') + 'Plugin'

    context = {"project": name,
               "description": description,
               "author": author,
               "author_email": email,
               "keywords": keywords,
               "github_user_name": github,
               "project_shortname": project_shortname,
               "plugin_class_name": plugin_class_name,
               "_source": "cli"}

    if output_dir == '.':
        os.chdir('../../../..')
        output_dir = os.getcwd()
    cookiecutter(template_loc, no_input=True, extra_context=context,
        output_dir=output_dir)
