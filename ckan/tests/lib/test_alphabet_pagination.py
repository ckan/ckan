import re

from nose.tools import assert_equal

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

    def test_00_model(self):
        query = model.Session.query(model.Package)
        page = h.AlphaPage(
            collection=query,
            alpha_attribute='title',
            page='A',
            other_text=other,
        )
        assert_equal(page.available, {'Other': 20, 'A': 10, 'C': 10, 'B': 10, 'E': 0, 'D': 10, 'G': 0, 'F': 0, 'I': 0, 'H': 0, 'K': 0, 'J': 0, 'M': 0, 'L': 0, 'O': 0, 'N': 0, 'Q': 0, 'P': 0, 'S': 0, 'R': 0, 'U': 0, 'T': 0, 'W': 0, 'V': 0, 'Y': 0, 'X': 0, 'Z': 0})

    def test_01_package_page(self):
        query = model.Session.query(model.Package)
        page = h.AlphaPage(
            collection=query,
            alpha_attribute='title',
            page='A',
            other_text=other,
        )
        pager = page.pager()
        assert pager.startswith('<div class="pagination pagination-alphabet">'), pager
        assert '<li class="active"><a href="/tag?page=A">A</a></li>' in pager, pager
        url_base = '/packages'
        assert re.search(r'\<li\>\<a href="\/tag\?page=B"\>B\<\/a\>\<\/li\>', pager), pager
        assert re.search(r'\<li class="disabled"\>\<a href="\/tag\?page=E"\>E\<\/a\>\<\/li\>', pager), pager
        assert re.search(r'\<li\>\<a href="\/tag\?page=Other"\>Other\<\/a\>\<\/li\>', pager), pager


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
