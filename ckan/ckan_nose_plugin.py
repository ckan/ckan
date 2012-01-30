from nose.plugins import Plugin
from inspect import isclass
import os
import sys
import pkg_resources
from paste.deploy import loadapp
from pylons import config

class CkanNose(Plugin):
    settings = None

    def startContext(self, ctx):
        # import needs to be here or setup happens too early
        import ckan.model as model

        if isclass(ctx):
            if hasattr(ctx, "no_db") and ctx.no_db:
                return
            if self.is_first_test or CkanNose.settings.ckan_migration:
                model.Session.close_all()
                model.repo.clean_db()
                self.is_first_test = False
                if CkanNose.settings.ckan_migration:
                    model.Session.close_all()
                    model.repo.upgrade_db()
            # init_db is run at the start of every class because
            # when you use an in-memory sqlite db, it appears that
            # the db is destroyed after every test when you Session.Remove().
            model.repo.init_db()

            ## This is to make sure the configuration is run again.
            ## Plugins use configure to make their own tables and they
            ## may need to be recreated to make tests work.
            from ckan.plugins import PluginImplementations
            from ckan.plugins.interfaces import IConfigurable
            for plugin in PluginImplementations(IConfigurable):
                plugin.configure(config)
            

    def options(self, parser, env):
        parser.add_option(
            '--ckan',
            action='store_true',
            dest='is_ckan',
            help='Always set this when testing CKAN.')
        parser.add_option(
            '--ckan-migration',
            action='store_true',
            dest='ckan_migration',
            help='set this when wanting to test migrations')
        parser.add_option(
            '--docstrings',
            action='store_true',
            dest='docstrings',
            help='set this to display test docstrings instead of module names')

    def configure(self, settings, config):
        CkanNose.settings = settings
        if settings.is_ckan:
            self.enabled = True
            self.is_first_test = True

    def describeTest(self, test):
        if not CkanNose.settings.docstrings:
            # display module name instead of docstring
            return False

