# encoding: utf-8

from nose.plugins import Plugin
from inspect import isclass
import hashlib
import os
import sys
import re
import pkg_resources
from paste.deploy import loadapp
from ckan.common import config
import unittest
import time

class CkanNose(Plugin):
    settings = None

    def startContext(self, ctx):
        # import needs to be here or setup happens too early
        import ckan.model as model

        if 'legacy' not in repr(ctx):
            # We don't want to do the stuff below for new-style tests.
            if not CkanNose.settings.reset_database:
                model.repo.tables_created_and_initialised = True
            return

        if isclass(ctx):
            if hasattr(ctx, "no_db") and ctx.no_db:
                return
            if (not CkanNose.settings.reset_database
                    and not CkanNose.settings.ckan_migration):
                model.Session.close_all()
                model.repo.tables_created_and_initialised = True
                model.repo.rebuild_db()
                self.is_first_test = False
            elif self.is_first_test or CkanNose.settings.ckan_migration:
                model.Session.close_all()
                model.repo.clean_db()
                self.is_first_test = False
                if CkanNose.settings.ckan_migration:
                    model.Session.close_all()
                    model.repo.upgrade_db()

            ## This is to make sure the configuration is run again.
            ## Plugins use configure to make their own tables and they
            ## may need to be recreated to make tests work.
            from ckan.plugins import PluginImplementations
            from ckan.plugins.interfaces import IConfigurable
            for plugin in PluginImplementations(IConfigurable):
                plugin.configure(config)

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
        parser.add_option(
            '--segments',
            dest='segments',
            help='A string containing a hex digits that represent which of'
                 'the 16 test segments to run. i.e 15af will run segments 1,5,a,f')
        parser.add_option(
            '--reset-db',
            action='store_true',
            dest='reset_database',
            help='drop database and reinitialize before tests are run')

    def wantClass(self, cls):
        if self.segments and str(hashlib.md5(
                cls.__name__).hexdigest())[0] not in self.segments:
            return False

    def wantFunction(self, fn):
        if self.segments and hashlib.md5(
                fn.__name__).hexdigest()[0] not in self.segments:
            return False

    def finalize(self, report):
        if self.segments:
            print 'Segments: %s' % self.segments

    def configure(self, settings, config):
        CkanNose.settings = settings
        if settings.is_ckan:
            self.enabled = True
            self.is_first_test = True
        self.segments = settings.segments

    def describeTest(self, test):
        if not CkanNose.settings.docstrings:
            # display module name instead of docstring
            return False

    def startTest(self, test):
        """
        startTest: start timing.
        """
##        self._started = time.time()

    def stopTest(self, test):
        """
        stopTest: stop timing, canonicalize the test name, and save
        the run time.
        """
##        runtime = time.time() - self._started
##
##        # CTB: HACK!
##        f = open('times.txt', 'a')
##
##        testname = str(test)
##        #if ' ' in testname:
##        #    testname = testname.split()[1]
##
##        f.write('%s,%s\n' % (testname, str(runtime)))
##
##        f.close()
