from ckan.tests import *
from pylons import config
from ckan.lib.base import BaseController
from ckan.lib.cache import cache
from time import gmtime, time, mktime, strptime, sleep
import sys

def now():
    return mktime(gmtime())
start = now()

class CacheController(BaseController):
    @cache()
    def defaults(self):
        return "defaults"

    @cache(test=lambda : start + 3600)
    def future(self):
        return "future"

    @cache(test=lambda : now())
    def always(self):
        return "always"
    
sys.modules["ckan.controllers.cache"] = __import__(__name__)
sys.modules["ckan.controllers.cache"].CacheController = CacheController

class TestCacheController(TestController):
    def test_defaults(self):
        """
        Check default behaviour, cache once, never expire
        """
        url = url_for(controller="cache", action="defaults")

        resp = self.app.get(url)
        headers = dict(resp.headers)

        # check last modified
        last_modified = headers["Last-Modified"]
        last_modified = strptime(last_modified, "%a, %d %b %Y %H:%M:%S GMT")
        assert mktime(last_modified) == 0, last_modified

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
        assert mktime(last_modified) == 0, last_modified

        # check no-cache does not appear
        assert "no-cache" not in headers["Cache-Control"], headers["Cache-Control"]
        assert "Pragma" not in headers

        # should have been a cache miss
        assert headers["X-CKAN-Cache"] == "HIT"

    def test_future(self):
        url = url_for(controller="cache", action="future")
        
        resp = self.app.get(url)
        headers = dict(resp.headers)

        # check last modified
        last_modified = headers["Last-Modified"]
        last_modified = strptime(last_modified, "%a, %d %b %Y %H:%M:%S GMT")
        last_modified = mktime(last_modified)
        assert last_modified == start + 3600, (start + 3600, last_modified)
        
        # should have been a cache miss
        assert headers["X-CKAN-Cache"] == "MISS"

    def test_always(self):
        """
        Check where last-modified is always now()
        """
        url = url_for(controller="cache", action="always")

        resp = self.app.get(url)
        headers = dict(resp.headers)
        first_modified = headers["Last-Modified"]
        first_modified = strptime(first_modified, "%a, %d %b %Y %H:%M:%S GMT")
        first_modified = mktime(first_modified)

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
        last_modified = mktime(last_modified)

        # check last-modified
        assert last_modified > first_modified, (first_modified, last_modified)

        # check no-cache does not appear
        assert "no-cache" not in headers["Cache-Control"], headers["Cache-Control"]
        assert "Pragma" not in headers

        # should have been a cache miss
        assert headers["X-CKAN-Cache"] == "MISS"

