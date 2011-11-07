from pylons import c, session
from pylons.i18n import set_lang

from ckan.lib.create_test_data import CreateTestData
from ckan.controllers.home import HomeController
import ckan.model as model

from ckan.tests import *
from ckan.tests.html_check import HtmlCheckMethods
from ckan.tests.pylons_controller import PylonsTestCase
from ckan.tests import search_related, setup_test_search_index

class TestHomeController(TestController, PylonsTestCase, HtmlCheckMethods):
    @classmethod
    def setup_class(cls):
        setup_test_search_index()
        PylonsTestCase.setup_class()
        model.repo.init_db()
        CreateTestData.create()
        
    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def clear_language_setting(self):
        self.app.cookies = {}

    def test_home_page(self):
        offset = url_for('home')
        res = self.app.get(offset)
        assert 'Add a dataset' in res
        assert 'Could not change language' not in res

    def test_calculate_etag_hash(self):
        # anything that changes the home page appearance should change the
        # etag hash
        c.user = 'test user'
        get_hash = HomeController._home_cache_key
        hashes = [get_hash(), get_hash()]
        self.assert_equal(hashes[0], hashes[1])

        def assert_hash_changed(hashes):
            current_hash = get_hash()
            assert current_hash != hashes[-1]
            hashes.append(current_hash)

        # login as a different user
        c.user = 'another user'
        assert_hash_changed(hashes)

        # add a package to a group
        rev = model.repo.new_revision()
        model.Group.by_name(u'roger').add_package_by_name(u'warandpeace')
        model.repo.commit_and_remove()
        assert_hash_changed(hashes)

        # flash message is not cached, but this is done in ckan/lib/cache
        
        # I can't get set_lang to work and deliver correct
        # result to get_lang, so leaving it commented
##        set_lang('fr')
##        assert_hash_changed(hashes)

    @search_related
    def test_packages_link(self):
        offset = url_for('home')
        res = self.app.get(offset)
        res.click('Search', index=0)
        
    def test_404(self):
        offset = '/some_nonexistent_url'
        res = self.app.get(offset, status=404)

    def test_guide(self):
        url = url_for('guide')
        assert url == 'http://wiki.okfn.org/ckan/doc/'

    def test_template_head_end(self):
        offset = url_for('home')
        res = self.app.get(offset)
        assert 'ckan.template_head_end = <link rel="stylesheet" href="TEST_TEMPLATE_HEAD_END.css" type="text/css"> '

    def test_template_footer_end(self):
        offset = url_for('home')
        res = self.app.get(offset)
        assert '<strong>TEST TEMPLATE_FOOTER_END TEST</strong>'

## Browser lang detection disabled - see #1452
##    def test_locale_detect(self):
##        offset = url_for('home')
##        self.clear_language_setting()
##        res = self.app.get(offset, headers={'Accept-Language': 'de,pt-br,en'})
##        try:
##            assert 'Willkommen' in res.body, res.body
##        finally:
##            self.clear_language_setting()

    def test_locale_negotiate(self):
        offset = url_for('home')
        self.clear_language_setting()
        res = self.app.get(offset, headers={'Accept-Language': 'fr-ca'})
        # Request for French with Canadian territory should negotiate to
        # just 'fr'
        try:
            assert 'propos' in res.body, res.body
        finally:
            self.clear_language_setting()

    def test_locale_negotiate_pt(self):
        offset = url_for('home')
        self.clear_language_setting()
        res = self.app.get(offset, headers={'Accept-Language': 'pt'})
        # Request for Portuguese should find pt_BR because of our alias hack
        try:
            assert 'Bem-vindo' in res.body, res.body
        finally:
            self.clear_language_setting()

    def test_locale_change(self):
        offset = url_for('home')
        res = self.app.get(offset)
        res = res.click('Deutsch')
        try:
            res = res.follow()
            assert 'Willkommen' in res.body
        finally:
            self.clear_language_setting()

    def test_locale_change_invalid(self):
        offset = url_for(controller='home', action='locale', locale='')
        res = self.app.get(offset, status=400)
        main_res = self.main_div(res)
        assert 'Invalid language specified' in main_res, main_res

    def test_locale_change_blank(self):
        offset = url_for(controller='home', action='locale')
        res = self.app.get(offset, status=400)
        main_res = self.main_div(res)
        assert 'No language given!' in main_res, main_res

    def test_locale_change_with_false_hash(self):
        offset = url_for('home')
        res = self.app.get(offset)
        found_html, found_desc, found_attrs = res._find_element(
            tag='a', href_attr='href',
            href_extract=None,
            content='Deutsch',
            id=None, 
            href_pattern=None,
            html_pattern=None,
            index=None, verbose=False)
        href = found_attrs['uri']
        assert href
        res = res.goto(href)
        try:
            assert res.status == 302, res.status # redirect

            href = href.replace('return_to=%2F&', 'return_to=%2Fhackedurl&')
            res = res.goto(href)
            assert res.status == 200, res.status # doesn't redirect
        finally:
            self.clear_language_setting()

class TestDatabaseNotInitialised(TestController):
    @classmethod
    def setup_class(cls):
        PylonsTestCase.setup_class()
        model.repo.clean_db()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_home_page(self):
        offset = url_for('home')
        res = self.app.get(offset, status=503)
        assert 'This site is currently off-line. Database is not initialised.' in res
