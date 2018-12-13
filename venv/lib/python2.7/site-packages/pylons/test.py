"""Test related functionality

Adds a Pylons plugin to `nose
<http://www.somethingaboutorange.com/mrl/projects/nose/>`_ that loads
the Pylons app *before* scanning for doc tests.

This can be configured in the projects :file:`setup.cfg` under a
``[nosetests]`` block:

.. code-block:: ini

    [nosetests]
    with-pylons=development.ini

Alternate ini files may be specified if the app should be loaded using
a different configuration.

"""
import os
import sys

import nose.plugins
import pkg_resources
from paste.deploy import loadapp

import pylons
from pylons.i18n.translation import _get_translator

pylonsapp = None

class PylonsPlugin(nose.plugins.Plugin):
    """Nose plugin extension

    For use with nose to allow a project to be configured before nose
    proceeds to scan the project for doc tests and unit tests. This
    prevents modules from being loaded without a configured Pylons
    environment.

    """
    enabled = False
    enableOpt = 'pylons_config'
    name = 'pylons'

    def add_options(self, parser, env=os.environ):
        """Add command-line options for this plugin"""
        env_opt = 'NOSE_WITH_%s' % self.name.upper()
        env_opt.replace('-', '_')

        parser.add_option("--with-%s" % self.name,
                          dest=self.enableOpt, type="string",
                          default="",
                          help="Setup Pylons environment with the config file"
                          " specified by ATTR [NOSE_ATTR]")

    def configure(self, options, conf):
        """Configure the plugin"""
        self.config_file = None
        self.conf = conf
        if hasattr(options, self.enableOpt):
            self.enabled = bool(getattr(options, self.enableOpt))
            self.config_file = getattr(options, self.enableOpt)

    def begin(self):
        """Called before any tests are collected or run

        Loads the application, and in turn its configuration.

        """
        global pylonsapp
        path = os.getcwd()
        sys.path.insert(0, path)
        pkg_resources.working_set.add_entry(path)
        self.app = pylonsapp = loadapp('config:' + self.config_file,
                                       relative_to=path)

        # Initialize a translator for tests that utilize i18n
        translator = _get_translator(pylons.config.get('lang'))
        pylons.translator._push_object(translator)
