"""
   Configuration parser module.
"""

from six.moves.configparser import ConfigParser

from migrate.versioning.config import *
from migrate.versioning import pathed


class Parser(ConfigParser):
    """A project configuration file."""

    def to_dict(self, sections=None):
        """It's easier to access config values like dictionaries"""
        return self._sections


class Config(pathed.Pathed, Parser):
    """Configuration class."""

    def __init__(self, path, *p, **k):
        """Confirm the config file exists; read it."""
        self.require_found(path)
        pathed.Pathed.__init__(self, path)
        Parser.__init__(self, *p, **k)
        self.read(path)
