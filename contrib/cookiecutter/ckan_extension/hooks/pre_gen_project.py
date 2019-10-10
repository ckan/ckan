# encoding: utf-8

import sys


def validate_project_name():
    # Check that project name begins with 'ckanext-'
    project_name = "{{ cookiecutter.project }}"
    if not project_name.startswith('ckanext-'):
        print("\nERROR: Project name must start with 'ckanext-' > {}"
              .format(project_name))
        sys.exit(1)


if __name__ == '__main__':
    validate_project_name()
