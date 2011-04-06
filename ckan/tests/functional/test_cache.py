from ckan.tests import *
from pylons import config
from ckan.lib.base import BaseController
import ckan.lib.cache
from ckan.lib.cache import ckan_cache, get_cache_expires
from time import gmtime, time, strptime, sleep
from calendar import timegm
import sys

def now():
    return timegm(gmtime())
start = now()

class TestCacheBasics:
    def setup(self):
        self.cache_enabled = ckan.lib.cache.cache_enabled

    def teardown(self):
        ckan.lib.cache.cache_enabled = self.cache_enabled

    def test_get_cache_expires(self):
        # cache enabled disabled by default
        out = get_cache_expires(sys.modules[__name__])
        assert out == -1, out

        ckan.lib.cache.cache_enabled  = True
        out = get_cache_expires(sys.modules[__name__])
        assert out == 1800, out

        out = get_cache_expires(self.test_get_cache_expires)
        assert out == 3600, out

        # no match, so use config default_expires
        out = get_cache_expires(ckan.lib.cache)
        assert out == 200, out


class CacheController(BaseController):
    """
    Dummy controller - we are testing the decorator
    not the controller
    """
    @ckan_cache()
    def defaults(self):
        return "defaults"

    @ckan_cache(test=lambda *av, **kw: start + 3600)
    def future(self):
        return "future"

    @ckan_cache(test=lambda *av, **kw: now())
    def always(self):
        return "always"
# put the dummy controller where routes can find it
# XXX FIXME THIS DOESN'T WORK
sys.modules["ckan.controllers.cache"] = __import__(__name__)
sys.modules["ckan.controllers.cache"].CacheController = CacheController

from nose.plugins.skip import SkipTest

class TestCacheController(TestController):
    def test_defaults(self):
        """
        Check default behaviour, cache once, never expire
        """
        raise SkipTest()
        url = url_for(controller="cache", action="defaults")

        resp = self.app.get(url)
        headers = dict(resp.headers)

        # check last modified
        last_modified = headers["Last-Modified"]
        last_modified = strptime(last_modified, "%a, %d %b %Y %H:%M:%S GMT")
        assert timegm(last_modified) == 0, last_modified

        # check no-cache does not appear
        assert "no-cache" not in headers["Cache-Control"], headers["Cache-Control"]
        assert "Pragma" not in headers

        # should have been a cache miss
        assert headers["X-CKAN-Cache"] == "MISS"

        resp = self.app.get(url)
        headers = dict(resp.headers)

        # check last modified
        last_modified = headers["Last-Modified"]
        last_modified = strptime(last_modified, "%a, %d %b %Y %H:%M:%S GMT")
        assert timegm(last_modified) == 0, last_modified

        # check no-cache does not appear
        assert "no-cache" not in headers["Cache-Control"], headers["Cache-Control"]
        assert "Pragma" not in headers

        # should have been a cache miss
        assert headers["X-CKAN-Cache"] == "HIT"

    def test_future(self):
        """
        Expiry in the future

        This should raise an exception as it is not allowed per HTTP/1.1
        """
        raise SkipTest()
        url = url_for(controller="cache", action="future")
        
        resp = self.app.get(url)
        headers = dict(resp.headers)

        # check last modified
        last_modified = headers["Last-Modified"]
        last_modified = strptime(last_modified, "%a, %d %b %Y %H:%M:%S GMT")
        last_modified = timegm(last_modified)
        assert last_modified == start + 3600, (start + 3600, last_modified)
        
        # should have been a cache miss
        assert headers["X-CKAN-Cache"] == "MISS"

    def test_always(self):
        """
        Check where last-modified is always now()
        """
        raise SkipTest()
        url = url_for(controller="cache", action="always")

        resp = self.app.get(url)
        headers = dict(resp.headers)
        first_modified = headers["Last-Modified"]
        first_modified = strptime(first_modified, "%a, %d %b %Y %H:%M:%S GMT")
        first_modified = timegm(first_modified)

        # check no-cache does not appear
        assert "no-cache" not in headers["Cache-Control"], headers["Cache-Control"]
        assert "Pragma" not in headers

        # should have been a cache miss
        assert headers["X-CKAN-Cache"] == "MISS"

        sleep(1)
        
        resp = self.app.get(url)
        headers = dict(resp.headers)
        last_modified = headers["Last-Modified"]
        last_modified = strptime(last_modified, "%a, %d %b %Y %H:%M:%S GMT")
        last_modified = timegm(last_modified)

        # check last-modified
        assert last_modified > first_modified, (first_modified, last_modified)

        # check no-cache does not appear
        assert "no-cache" not in headers["Cache-Control"], headers["Cache-Control"]
        assert "Pragma" not in headers

        # should have been a cache miss
        assert headers["X-CKAN-Cache"] == "MISS"

