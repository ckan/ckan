from nose.plugins import Plugin
from inspect import isclass
import os


class CkanNose(Plugin):

    def startContext(self, ctx):
        # import needs to be here or setup happens too early
        import ckan.model as model

        if self.is_first_test:
            model.repo.clean_db()
            self.is_first_test = False

        # init_db is run at the start of every class because
        # when you use an in-memory sqlite db, it appears that
        # the db is destroyed after every test when you Session.Remove().
        if isclass(ctx):
            if self.options.ckan_migration:
                model.repo.clean_db()
                model.repo.upgrade_db()

            model.repo.init_db()

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

    def configure(self, options, config):
        self.options = options
        if options.is_ckan:
            self.enabled = True
            self.is_first_test = True
