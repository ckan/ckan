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
import re
from unittest import TestCase
from nose.tools import assert_equal, assert_not_equal, make_decorator
from nose.plugins.skip import SkipTest
import time

from pylons import config
from pylons.test import pylonsapp
from paste.script.appinstall import SetupCommand

import pkg_resources
import paste.fixture
import paste.script.appinstall
from paste.deploy import loadapp

from ckan.lib.create_test_data import CreateTestData
from ckan.lib import search
from ckan.lib.helpers import _flash, url_for
from ckan.lib.helpers import json
import ckan.model as model
from ckan import ckan_nose_plugin

__all__ = ['url_for',
           'TestController',
           'CreateTestData',
           'TestSearchIndexer',
           'CheckMethods',
           'CommonFixtureMethods',
           'TestCase',
           'SkipTest',
           'CkanServerCase',
        ]

here_dir = os.path.dirname(os.path.abspath(__file__))
conf_dir = os.path.dirname(os.path.dirname(here_dir))

# Invoke websetup with the current config file
SetupCommand('setup-app').run([config['__file__']])

# monkey patch paste.fixtures.TestRespose
# webtest (successor library) already has this
# http://pythonpaste.org/webtest/#parsing-the-body
def _getjson(self):
    return json.loads(self.body)
paste.fixture.TestResponse.json = property(_getjson)

# Check config is correct for sqlite
if model.engine_is_sqlite():
    assert ckan_nose_plugin.CkanNose.settings.is_ckan, \
           'You forgot the "--ckan" nosetest setting - see doc/test.rst'

class BaseCase(object):

    def setup(self):
        pass

    def teardown(self):
        pass

    @staticmethod
    def _system(cmd):
        import commands
        (status, output) = commands.getstatusoutput(cmd)
        if status:
            raise Exception, "Couldn't execute cmd: %s: %s" % (cmd, output)

    @classmethod
    def _paster(cls, cmd, config_path_rel):
        config_path = os.path.join(config['here'], config_path_rel)
        cls._system('paster --plugin ckan %s --config=%s' % (cmd, config_path))


class CommonFixtureMethods(BaseCase):

    @classmethod
    def create_package(self, data={}, admins=[], **kwds):
        # Todo: A simpler method for just creating a package.
        CreateTestData.create_arbitrary(package_dicts=[data or kwds], admins=admins)

    @classmethod
    def create_user(cls, **kwds):
        user = model.User(name=kwds['name'])             
        model.Session.add(user)
        model.Session.commit()
        model.Session.remove()
        return user

    @staticmethod
    def get_package_by_name(package_name):
        return model.Package.by_name(package_name)

    @staticmethod
    def get_group_by_name(group_name):
        return model.Group.by_name(group_name)

    @staticmethod
    def get_user_by_name(name):
        return model.User.by_name(name)

    @staticmethod
    def get_tag_by_name(name):
        return model.Tag.by_name(name)

    def purge_package_by_name(self, package_name):
        package = self.get_package_by_name(package_name)
        if package:
            package.purge()
            model.repo.commit_and_remove()

    @classmethod
    def purge_packages(cls, pkg_names):
        for pkg_name in pkg_names:
            pkg = model.Package.by_name(unicode(pkg_name))
            if pkg:
                pkg.purge()
        model.repo.commit_and_remove()

    @classmethod
    def purge_all_packages(self):
        all_pkg_names = [pkg.name for pkg in model.Session.query(model.Package)]
        self.purge_packages(all_pkg_names)

    def purge_group_by_name(self, group_name):
        group = self.get_group_by_name(group_name)
        if group:
            group.purge()
            model.repo.commit_and_remove()

    @classmethod
    def clear_all_tst_ratings(self):
        ratings = model.Session.query(model.Rating).filter_by(package=model.Package.by_name(u'annakarenina')).all()
        ratings += model.Session.query(model.Rating).filter_by(package=model.Package.by_name(u'warandpeace')).all()
        for rating in ratings[:]:
            model.Session.delete(rating)
        model.repo.commit_and_remove()

    @property
    def war(self):
        return self.get_package_by_name(u'warandpeace')

    @property
    def anna(self):
        return self.get_package_by_name(u'annakarenina')

    @property
    def roger(self):
        return self.get_group_by_name(u'roger')

    @property
    def david(self):
        return self.get_group_by_name(u'david')

    @property
    def russian(self):
        return self.get_tag_by_name(u'russian')

    @property
    def tolstoy(self):
        return self.get_tag_by_name(u'tolstoy')

    @property
    def flexible_tag(self):
        return self.get_tag_by_name(u'Flexible \u30a1')

class CheckMethods(BaseCase):

    def assert_true(self, value):
        assert value, "Not true: '%s'" % value

    def assert_false(self, value):
        assert not value, "Not false: '%s'" % value

    def assert_equal(self, value1, value2):
        assert value1 == value2, 'Not equal: %s' % ((value1, value2),)

    def assert_isinstance(self, value, check):
        assert isinstance(value, check), 'Not an instance: %s' % ((value, check),)
    
    def assert_raises(self, exception_class, callable, *args, **kwds): 
        try:
            callable(*args, **kwds)
        except exception_class:
            pass
        else:
            assert False, "Didn't raise '%s' when calling: %s with %s" % (exception_class, callable, (args, kwds))

    def assert_contains(self, sequence, item):
        assert item in sequence, "Sequence %s does not contain item: %s" % (sequence, item)

    def assert_missing(self, sequence, item):
        assert item not in sequence, "Sequence %s does contain item: %s" % (sequence, item)

    def assert_len(self, sequence, count):
        assert len(sequence) == count, "Length of sequence %s was not %s." % (sequence, count)

    def assert_isinstance(self, object, kind):
        assert isinstance(object, kind), "Object %s is not an instance of %s." % (object, kind)


class TestCase(CommonFixtureMethods, CheckMethods, BaseCase):
    def setup(self):
        super(TestCase, self).setup()
        self.conditional_create_common_fixtures()

    def teardown(self):
        self.reuse_or_delete_common_fixtures()
        super(TestCase, self).setup()


class WsgiAppCase(BaseCase):
    wsgiapp = pylonsapp
    assert wsgiapp, 'You need to run nose with --with-pylons'
    # Either that, or this file got imported somehow before the tests started
    # running, meaning the pylonsapp wasn't setup yet (which is done in
    # pylons.test.py:begin())
    app = paste.fixture.TestApp(wsgiapp)


def config_abspath(file_path):
            if os.path.isabs(file_path):
                return file_path
            return os.path.join(conf_dir, file_path)

class CkanServerCase(BaseCase):
    @classmethod
    def _recreate_ckan_server_testdata(cls, config_path):
        cls._paster('db clean', config_path)
        cls._paster('db init', config_path)
        cls._paster('create-test-data', config_path)
        cls._paster('search-index rebuild', config_path)

    @staticmethod
    def _start_ckan_server(config_file=None):
        if not config_file:
            config_file = config['__file__']
        config_path = config_abspath(config_file)
        import subprocess
        process = subprocess.Popen(['paster', 'serve', config_path])
        return process

    @staticmethod
    def _wait_for_url(url='http://127.0.0.1:5000/', timeout=15):
        for i in range(int(timeout)*100):
            import urllib2
            import time
            try:
                response = urllib2.urlopen(url)
            except urllib2.URLError:
                time.sleep(0.01)
            else:
                break

    @staticmethod
    def _stop_ckan_server(process): 
        pid = process.pid
        pid = int(pid)
        if os.system("kill -9 %d" % pid):
            raise Exception, "Can't kill foreign CKAN instance (pid: %d)." % pid


class TestController(CommonFixtureMethods, CkanServerCase, WsgiAppCase, BaseCase):

    def assert_equal(self, *args, **kwds):
        assert_equal(*args, **kwds)

    def assert_not_equal(self, *args, **kwds):
        assert_not_equal(*args, **kwds)

    def clear_language_setting(self):
        self.app.cookies = {}


class TestSearchIndexer:
    '''
    Tests which use search can use this object to provide indexing
    Usage:
    self.tsi = TestSearchIndexer()
     (create packages)
    self.tsi.index()
     (do searching)
    ''' 
    
    def __init__(self):
        from ckan import plugins
        if not is_search_supported():
            raise SkipTest("Search not supported")
        plugins.load('synchronous_search')

    @classmethod
    def index(cls):
        pass     

    @classmethod
    def list(cls):
        return [model.Package.get(pkg_index.package_id).name for pkg_index in model.Session.query(model.PackageSearch)]
            
def setup_test_search_index():
    from ckan import plugins
    if not is_search_supported():
        raise SkipTest("Search not supported")
    search.clear()
    plugins.load('synchronous_search')

def is_search_supported():
    is_supported_db = not model.engine_is_sqlite()
    return is_supported_db

def is_regex_supported():
    is_supported_db = not model.engine_is_sqlite()
    return is_supported_db

def is_migration_supported():
    is_supported_db = not model.engine_is_sqlite()
    return is_supported_db

def search_related(test):
    def skip_test(*args):
        raise SkipTest("Search not supported")
    if not is_search_supported():
        return make_decorator(test)(skip_test)
    return test

def regex_related(test):
    def skip_test(*args):
        raise SkipTest("Regex not supported")
    if not is_regex_supported():
        return make_decorator(test)(skip_test)
    return test

def clear_flash(res=None):
    messages = _flash.pop_messages()
