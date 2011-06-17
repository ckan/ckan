import cgi

from paste.fixture import AppError
from pylons import config
from pylons import c
from genshi.core import escape as genshi_escape
from difflib import unified_diff
from nose.plugins.skip import SkipTest

from ckan.tests import *
from ckan.tests.html_check import HtmlCheckMethods
from ckan.tests.pylons_controller import PylonsTestCase
from ckan.lib.create_test_data import CreateTestData
from ckan import model
from test_package import TestPackageForm as _TestPackageForm

class TestAutoneg(_TestPackageForm, PylonsTestCase):
    @classmethod
    def setup_class(cls):
        PylonsTestCase.setup_class()
        CreateTestData.create()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_default(self):
        url = url_for(controller='package', action='read', id='annakarenina')
        response = self.app.get(url)
        assert response.status == 200, response.status
        content_type = response.header("Content-Type")
        assert "html" in content_type, content_type

    def test_chrome(self):
        url = url_for(controller='package', action='read', id='annakarenina')
        ## this is what chrome sends... notice how it prefers pictures of web pages
        ## to web pages
        accept = "application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png,*/*;q=0.5"
        response = self.app.get(url, headers={"Accept": accept})
        assert response.status == 200, response.status
        content_type = response.header("Content-Type")
        assert "html" in content_type, content_type

    def test_firefox(self):
        url = url_for(controller='package', action='read', id='annakarenina')
        ## this is what firefox sends
        accept = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        response = self.app.get(url, headers={"Accept": accept})
        assert response.status == 200, response.status
        content_type = response.header("Content-Type")
        assert "html" in content_type, content_type

    def test_html_rdf(self):
        url = url_for(controller='package', action='read', id='annakarenina')
        ## this is an important test. rdf appears first, but with a lower priority
        ## than html. we expect to get html back
        accept = "application/rdf+xml;q=0.5,application/xhtml+xml,text/html;q=0.9"
        response = self.app.get(url, headers={"Accept": accept})
        assert response.status == 200, response.status
        content_type = response.header("Content-Type")
        assert "html" in content_type, content_type
        
    def test_rdfxml(self):
        url = url_for(controller='package', action='read', id='annakarenina')
        response = self.app.get(url, headers={"Accept": "application/rdf+xml"})
        assert response.status == 303, response.status
        location = response.header("Location")
        assert location.endswith(".rdf"), location
        assert location.startswith('http://test.com/package/'), location

    def test_turtle(self):
        url = url_for(controller='package', action='read', id='annakarenina')
        response = self.app.get(url, headers={"Accept": "application/turtle"})
        assert response.status == 303, response.status
        location = response.header("Location")
        assert location.endswith(".ttl"), location
        assert location.startswith('http://test.com/package/'), location

