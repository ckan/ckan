"""Pylons application test package

When the test runner finds and executes tests within this directory,
this file will be loaded to setup the test environment.

It registers the root directory of the project in sys.path and
pkg_resources, in case the project hasn't been installed with
setuptools. It also initializes the application via websetup (paster
setup-app) with the project's test.ini configuration file.
"""
import os
import sys
from unittest import TestCase

import pkg_resources
import paste.fixture
import paste.script.appinstall
from paste.deploy import loadapp
from routes import url_for

__all__ = ['url_for',
        # cannot include this as it breaks py.test ...
        # 'TestController',
        'TestController2',
        'TestData',
        'create_test_data' ]

here_dir = os.path.dirname(os.path.abspath(__file__))
conf_dir = os.path.dirname(os.path.dirname(here_dir))

sys.path.insert(0, conf_dir)
pkg_resources.working_set.add_entry(conf_dir)
pkg_resources.require('Paste')
pkg_resources.require('PasteScript')

test_file = os.path.join(conf_dir, 'test.ini')

cmd = paste.script.appinstall.SetupCommand('setup-app')
cmd.run([test_file])

class TestController(TestCase):

    def __init__(self, *args, **kwargs):
        wsgiapp = loadapp('config:test.ini', relative_to=conf_dir)
        self.app = paste.fixture.TestApp(wsgiapp)
        TestCase.__init__(self, *args, **kwargs)

class TestController2(object):

    def __init__(self, *args, **kwargs):
        wsgiapp = loadapp('config:test.ini', relative_to=conf_dir)
        self.app = paste.fixture.TestApp(wsgiapp)
        self.transaction = None

    def transaction_begin(self):
        import ckan.models
        if self.transaction == None:
            self.transaction = ckan.models.repo.begin_transaction()
        else:
            raise Exception, "Already in a transaction. Missing commit?"

    def transaction_commit(self):
        if self.transaction:
            self.transaction.commit()
            self.transaction = None
        else:
            raise Exception, "Not in a transaction. Missing begin?"

    def get_model(self):
        if not self.transaction:
            self.transaction_begin()
        return self.transaction.model

    def create_100_packages(self):
        listRegister = self.get_model().packages
        for i in range(0,100):
            name = "testpackage%s" % i
            listRegister.create(name=name)
        self.transaction_commit()

    def purge_100_packages(self):
        listRegister = self.get_model().packages
        for i in range(0,100):
            name = "testpackage%s" % i
            listRegister.purge(name)
        self.transaction_commit()

    def create_100_tags(self):
        listRegister = self.get_model().tags
        for i in range(0,100):
            name = "testtag%s" % i
            listRegister.create(name=name)
            print "Created tag: %s" % name
        self.transaction_commit()

    def purge_100_tags(self):
        listRegister = self.get_model().tags
        for i in range(0,100):
            name = "testtag%s" % i
            listRegister.purge(name)
        self.transaction_commit()


from ckan.lib.cli import TestData
def create_test_data():
    TestData.create()

