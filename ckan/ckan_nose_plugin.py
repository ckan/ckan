from nose.plugins import Plugin
from inspect import isclass
import os
import sys
import pkg_resources
from paste.deploy import loadapp

pylonsapp = None

class CkanNose(Plugin):

    def startContext(self, ctx):
        # import needs to be here or setup happens too early
        import ckan.model as model

        if isclass(ctx):
            if self.is_first_test:
                model.repo.clean_db()
                self.is_first_test = False
            # init_db is run at the start of every class because
            # when you use an in-memory sqlite db, it appears that
            # the db is destroyed after every test when you Session.Remove().
            model.repo.init_db()

    def options(self, parser, env):
        parser.add_option(
            '--ckan',
            action='store_true',
            dest='is_ckan',
            help='Always set this when testing CKAN.')
        
    def configure(self, options, config):
        if options.is_ckan or options.ckan_config:
            self.enabled = True
            self.is_first_test = True
