# encoding: utf-8

from . import ckan

if __name__ == "__main__":
    """
    Run CKAN CLI without installing CKAN as package.
    Useful for development and debugging purposes.

    Example:
      $ python3 -m ckan.cli.cli -c test-core.ini run --host 0.0.0.0
    """
    ckan()
