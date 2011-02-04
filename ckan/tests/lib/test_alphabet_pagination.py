import re

from ckan.tests import *
from ckan.tests import regex_related
from ckan.lib.create_test_data import CreateTestData
from ckan import model
import ckan.lib.helpers as h

other = 'Other'

class TestPages:
    @classmethod
    def setup_class(cls):
        # create data
        model.repo.init_db()
        pkgs = []
        for letter in 'abcd12':
            for i in range(0, 10):
                name = u'testpackage_%s_%s' % (letter, i)
                pkgs.append({
                    'name': u'testpackage_%s_%s' % (letter, i),
                    'title': u'%s Testpackage %s' % (letter, i),
                    })
        cls.num_pkgs = len(pkgs)
        CreateTestData.create_arbitrary(pkgs)

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_01_package_page(self):
        query = model.Session.query(model.Package)
        page = h.AlphaPage(
            collection=query,
            alpha_attribute='title',
            page='A',
            other_text=other,
        )
        pager = page.pager()
        assert pager.startswith('<div class="pager">'), pager
        assert '<span class="pager_curpage">A</span>' in pager, pager
        url_base = '/packages'
        assert re.search('\<a class="pager_link" href="[^?]*\?page=B"\>B\<\/a\>', pager), pager
        assert re.search('\<a class="pager_link" href="[^?]*\?page=Other"\>Other\<\/a\>', pager), pager


    def test_02_package_items(self):
        query = model.Session.query(model.Package)
        page = h.AlphaPage(
            collection=query,
            alpha_attribute='title',
            page='B',
            other_text=other,
        )
        items = page.items
        assert len(items) == 10, items
        for item in items:
            assert item.title.startswith('b'), item.title

    @regex_related
    def test_03_package_other_items(self):
        query = model.Session.query(model.Package)
        page = h.AlphaPage(
            collection=query,
            alpha_attribute='title',
            page=other,
            other_text=other,
        )
        items = page.items
        assert len(items) == 20, [item.title for item in items]
        for item in items:
            assert item.title.startswith('1') or item.title.startswith('2'), item.title

    def test_04_count(self):
        query = model.Session.query(model.Package)
        page = h.AlphaPage(
            collection=query,
            alpha_attribute='title',
            page=other,
            other_text=other,
        )
        assert page.item_count == self.num_pkgs, page.item_count

class TestTooFewToPage:
    @classmethod
    def setup_class(cls):
        # create data
        model.repo.init_db()
        pkgs = []
        for letter in 'abcd12':
            for i in range(0, 1):
                name = u'testpackage_%s_%s' % (letter, i)
                pkgs.append({
                    'name': u'testpackage_%s_%s' % (letter, i),
                    'title': u'%s Testpackage %s' % (letter, i),
                    })
        cls.num_pkgs = len(pkgs)
        CreateTestData.create_arbitrary(pkgs)

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_01_package_page(self):
        query = model.Session.query(model.Package)
        page = h.AlphaPage(
            collection=query,
            alpha_attribute='title',
            page='A',
            other_text=other,
        )
        pager = page.pager()
        assert not pager

    def test_02_package_items(self):
        query = model.Session.query(model.Package)
        page = h.AlphaPage(
            collection=query,
            alpha_attribute='title',
            page='B',
            other_text=other,
        )
        items = page.items
        assert len(items) == self.num_pkgs, items
