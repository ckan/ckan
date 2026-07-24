# encoding: utf-8

import os
from ckan.common import asbool
from ckan.cli.generate import remove_code_examples


def recut():
    """
    Remove unnecessary code examples
    """

    # Location for resulting file
    destination = os.getcwd()

    if not asbool("{{ cookiecutter.include_examples }}"):
        remove_code_examples(
            os.path.join(destination, "ckanext", "{{ cookiecutter.project_shortname }}")
        )


if __name__ == "__main__":
    if "{{ cookiecutter._source }}" == "local":
        recut()
