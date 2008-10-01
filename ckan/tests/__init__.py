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

from ckan.lib.cli import CreateTestData

__all__ = ['url_for',
        'TestController2',
        'CreateTestData',
        ]

here_dir = os.path.dirname(os.path.abspath(__file__))
conf_dir = os.path.dirname(os.path.dirname(here_dir))

sys.path.insert(0, conf_dir)
pkg_resources.working_set.add_entry(conf_dir)
pkg_resources.require('Paste')
pkg_resources.require('PasteScript')

test_file = os.path.join(conf_dir, 'test.ini')

cmd = paste.script.appinstall.SetupCommand('setup-app')
cmd.run([test_file])

import ckan.model as model

class TestController2(object):

    def __init__(self, *args, **kwargs):
        wsgiapp = loadapp('config:test.ini', relative_to=conf_dir)
        self.app = paste.fixture.TestApp(wsgiapp)

    def create_100_packages(self):
        rev = model.new_revision()
        for i in range(0,100):
            name = u"testpackage%s" % i
            model.Package(name=name)
        model.Session.commit()
        model.Session.remove()

    def purge_100_packages(self):
        listRegister = self.get_model().packages
        for i in range(0,100):
            name = u"testpackage%s" % i
            pkg = model.Package.by_name(name)
            pkg.purge(name)
        model.Session.commit()
        model.Session.remove()

    def create_100_tags(self):
        for i in range(0,100):
            name = u"testtag%s" % i
            model.Tag(name=name)
            print "Created tag: %s" % name
        model.Session.commit()
        model.Session.remove()

    def purge_100_tags(self):
        for i in range(0,100):
            name = u"testtag%s" % i
            tag = model.Tag.by_name(name)
            tag.purge()
        model.Session.commit()
        model.Session.remove()

