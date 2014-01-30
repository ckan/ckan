import datetime

from pylons import config, c
from genshi.core import escape as genshi_escape
from difflib import unified_diff
from nose.tools import assert_equal

from ckan.tests import *
import ckan.tests as tests
from ckan.tests.html_check import HtmlCheckMethods
from ckan.tests.pylons_controller import PylonsTestCase
from base import FunctionalTestCase
import ckan.model as model
from ckan.lib.create_test_data import CreateTestData
from ckan.logic.action import get, update
from ckan import plugins
from ckan.lib.search.common import SolrSettings




existing_extra_html = ('<label class="field_opt" for="Package-%(package_id)s-extras-%(key)s">%(capitalized_key)s</label>', '<input id="Package-%(package_id)s-extras-%(key)s" name="Package-%(package_id)s-extras-%(key)s" size="20" type="text" value="%(value)s">')


class TestPackageBase(FunctionalTestCase):
    key1 = u'key1 Less-than: < Umlaut: \xfc'
    value1 = u'value1 Less-than: < Umlaut: \xfc'
    # Note: Can't put a quotation mark in key1 or value1 because
    # paste.fixture doesn't unescape the value in an input field
    # on form submission. (But it works in real life.)

    def _assert_form_errors(self, res):
        self.check_tag(res, '<form', 'has-errors')
        assert 'field_error' in res, res

    def diff_responses(self, res1, res2):
        return self.diff_html(res1.body, res2.body)

    def diff_html(self, html1, html2):
        return '\n'.join(unified_diff(html1.split('\n'),
                                      html2.split('\n')))

class TestPackageForm(TestPackageBase):
    '''Inherit this in tests for these form testing methods'''
    def _check_package_read(self, res, **params):
        assert not 'Error' in res, res
        assert u'%s - Datasets' % params['title'] in res, res
        main_res = self.main_div(res)
        main_div = main_res
        main_div_str = main_div.encode('utf8')
        assert params['name'] in main_div, main_div_str
        assert params['title'] in main_div, main_div_str
        assert params['version'] in main_div, main_div_str
        self.check_named_element(main_div, 'a', 'href="%s"' % params['url'])
        prefix = 'Dataset-%s-' % params.get('id', '')
        for res_index, values in self._get_resource_values(params['resources'], by_resource=True):
            self.check_named_element(main_div, 'tr', *values)
        assert params['notes'] in main_div, main_div_str
        license = model.Package.get_license_register()[params['license_id']]
        assert license.title in main_div, (license.title, main_div_str)
        tag_names = list(params['tags'])
        self.check_named_element(main_div, 'ul', *tag_names)
        if params.has_key('state'):
            assert 'State: %s' % params['state'] in main_div.replace('</strong>', ''), main_div_str
        if isinstance(params['extras'], dict):
            extras = []
            for key, value in params['extras'].items():
                extras.append((key, value, False))
        elif isinstance(params['extras'], (list, tuple)):
            extras = params['extras']
        else:
            raise NotImplementedError
        for key, value, deleted in extras:
            if not deleted:
                key_in_html_body = self.escape_for_html_body(key)
                value_in_html_body = self.escape_for_html_body(value)
                self.check_named_element(main_div, 'tr', key_in_html_body, value_in_html_body)
            else:
                self.check_named_element(main_div, 'tr', '!' + key)
                self.check_named_element(main_div, 'tr', '!' + value)


    def _get_resource_values(self, resources, by_resource=False):
        assert isinstance(resources, (list, tuple))
        for res_index, resource in enumerate(resources):
            if by_resource:
                values = []
            for i, res_field in enumerate(model.Resource.get_columns(extra_columns = False)):
                if isinstance(resource, (str, unicode)):
                    expected_value = resource if res_field == 'url' else ''
                elif hasattr(resource, res_field):
                    expected_value = getattr(resource, res_field)
                elif isinstance(resource, (list, tuple)):
                    expected_value = resource[i]
                elif isinstance(resource, dict):
                    expected_value = resource.get(res_field, u'')
                else:
                    raise NotImplemented
                if not by_resource:
                    yield (res_index, res_field, expected_value)
                else:
                    values.append(expected_value)
            if by_resource:
                yield(res_index, values)

    def escape_for_html_body(self, unescaped_str):
        # just deal with chars in tests
        return unescaped_str.replace('<', '&lt;')

    def check_form_filled_correctly(self, res, **params):
        if params.has_key('pkg'):
            for key, value in params['pkg'].as_dict().items():
                if key == 'license':
                    key = 'license_id'
                params[key] = value
        prefix = ''
        main_res = self.main_div(res)
        self.check_tag(main_res, prefix+'name', params['name'])
        self.check_tag(main_res, prefix+'title', params['title'])
        self.check_tag(main_res, prefix+'version', params['version'])
        self.check_tag(main_res, prefix+'url', params['url'])
        #for res_index, res_field, expected_value in self._get_resource_values(params['resources']):
        #    ## only check fields that are on the form
        #    if res_field not in ['url', 'id', 'description', 'hash']:
        #        continue
        #    self.check_tag(main_res, '%sresources__%i__%s' % (prefix, res_index, res_field), expected_value)
        self.check_tag_and_data(main_res, prefix+'notes', params['notes'])
        self.check_tag_and_data(main_res, 'selected', params['license_id'])
        if isinstance(params['tags'], (str, unicode)):
            tags = map(lambda s: s.strip(), params['tags'].split(','))
        else:
            tags = params['tags']
        for tag in tags:
            self.check_tag(main_res, prefix+'tag_string', tag)
        if params.has_key('state'):
            self.check_tag_and_data(main_res, 'selected', str(params['state']))
        if isinstance(params['extras'], dict):
            extras = []
            for key, value in params['extras'].items():
                extras.append((key, value, False))
        else:
            extras = params['extras']
        for num, (key, value, deleted) in enumerate(sorted(extras)):
            key_in_html_body = self.escape_for_html_body(key)
            value_in_html_body = self.escape_for_html_body(value)
            key_escaped = genshi_escape(key)
            value_escaped = genshi_escape(value)
            self.check_tag(main_res, 'extras__%s__key' % num, key_in_html_body)
            self.check_tag(main_res, 'extras__%s__value' % num, value_escaped)
            if deleted:
                self.check_tag(main_res, 'extras__%s__deleted' % num, 'checked')

        assert params['log_message'] in main_res, main_res

    def _check_redirect(self, return_url_param, expected_redirect,
                        pkg_name_to_edit='',extra_environ=None):
        '''
        @param return_url_param - encoded url to be given as param - if None
                       then assume redirect is specified in pylons config
        @param expected_redirect - url we expect to redirect to (but <NAME>
                       not yet substituted)
        @param pkg_name_to_edit - '' means create a new dataset
        '''
        try:
            new_name = u'new-name'
            offset_params = {'controller':'package'}
            if pkg_name_to_edit:
                pkg_name = pkg_name_to_edit
                pkg = model.Package.by_name(pkg_name)
                assert pkg
                pkg_id = pkg.id
                offset_params['action'] = 'edit'
                offset_params['id'] = pkg_name_to_edit
            else:
                offset_params['action'] = 'new'
                pkg_id = ''
            if return_url_param:
                offset_params['return_to'] = return_url_param
            offset = url_for(**offset_params)
            res = self.app.get(offset, extra_environ=extra_environ)
            assert 'Datasets -' in res
            fv = res.forms['dataset-edit']
            prefix = ''
            fv[prefix + 'name'] = new_name
            res = fv.submit('save', status=302, extra_environ=extra_environ)
            assert not 'Error' in res, res
            redirected_to = dict(res.headers).get('Location') or dict(res.headers)['location']
            expected_redirect_url = expected_redirect.replace('<NAME>', new_name)
            assert redirected_to == expected_redirect_url, \
                   'Redirected to %s but should have been %s' % \
                   (redirected_to, expected_redirect_url)
        finally:
            # revert name change or pkg creation
            pkg = model.Package.by_name(new_name)
            if pkg:
                rev = model.repo.new_revision()
                if pkg_name_to_edit:
                    pkg.name = pkg_name_to_edit
                else:
                    pkg.purge()
                model.repo.commit_and_remove()

class TestReadOnly(TestPackageForm, HtmlCheckMethods, PylonsTestCase):

    @classmethod
    def setup_class(cls):
        PylonsTestCase.setup_class()
        CreateTestData.create()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_read(self):
        name = u'annakarenina'
        c.hide_welcome_message = True
        offset = url_for(controller='package', action='read', id=name)
        res = self.app.get(offset)
        # check you get the same html when specifying the pkg by id
        # instead of by name
        offset = url_for(controller='package', action='read', id=self.anna.id)
        res_by_id = self.app.get(offset)
        # just check the stuff in the package div
        pkg_by_name_main = self.named_div('dataset', res)
        pkg_by_id_main = self.named_div('dataset', res_by_id)
        # rename some things which may be in the wrong order sometimes
        txt_order_non_deterministic = (u'Flexible \u30a1', 'russian', 'tolstoy', 'david', 'roger')
        for txt in txt_order_non_deterministic:
            for pkg_ in (pkg_by_name_main, pkg_by_id_main):
                pkg_ = pkg_.replace(txt, 'placeholder')
        print pkg_by_name_main
        res_diff = self.diff_html(pkg_by_name_main, pkg_by_id_main)
        assert not res_diff, res_diff.encode('utf8')
        # not true as language selection link return url differs:
        #assert len(res_by_id.body) == len(res.body)

        # only retrieve after app has been called
        anna = self.anna
        assert name in res
        assert anna.version in res
        assert anna.url in res
        assert 'Some test notes' in res
        assert '<strong>Some bolded text.</strong>' in res
        self.check_tag_and_data(res, 'left arrow', '&lt;')
        self.check_tag_and_data(res, 'umlaut', u'\xfc')
        #assert 'OKD Compliant::' in res
        assert u'Flexible \u30a1' in res, res
        assert 'russian' in res
        assert 'david' in res
        assert 'roger' in res
        assert 'genre' in res, res
        assert 'romantic novel' in res, res
        assert 'original media' in res, res
        assert 'book' in res, res
        assert 'This dataset satisfies the Open Definition' in res, res

    def test_read_war_rdf(self):
        name = u'warandpeace'
        offset = url_for(controller='package', action='read', id=name + ".rdf")
        res = self.app.get(offset)
        assert '<dct:title>A Wonderful Story</dct:title>' in res, res


    def test_read_war(self):
        name = u'warandpeace'
        c.hide_welcome_message = True
        offset = url_for(controller='package', action='read', id=name)
        res = self.app.get(offset)
        assert 'This dataset is Not Open' in res, res

    def test_read_nonexistentpackage(self):
        name = 'anonexistentpackage'
        offset = url_for(controller='package', action='read', id=name)
        res = self.app.get(offset, status=404)

    def test_read_internal_links(self):
        pkg_name = u'link-test',
        CreateTestData.create_arbitrary([
            {'name':pkg_name,
             'notes':'Decoy link here: decoy:decoy, real links here: dataset:pkg-1, ' \
                   'tag:tag_1 group:test-group-1 and a multi-word tag: tag:"multi word with punctuation."',
             }
            ])
        offset = url_for(controller='package', action='read', id=pkg_name)
        res = self.app.get(offset)
        def check_link(res, controller, id):
            id_in_uri = id.strip('"').replace(' ', '%20') # remove quotes and percent-encode spaces
            self.check_tag_and_data(res, 'a ', '%s/%s' % (controller, id_in_uri),
                                    '%s:%s' % (controller, id.replace('"', '&#34;')))
        check_link(res, 'dataset', 'pkg-1')
        check_link(res, 'tag', 'tag_1')
        check_link(res, 'tag', '"multi word with punctuation."')
        check_link(res, 'group', 'test-group-1')
        assert 'decoy</a>' not in res, res
        assert 'decoy"' not in res, res

        #res = self.app.get(offset)
        #assert 'Datasets' in res
        #name = u'annakarenina'
        #title = u'A Novel By Tolstoy'
        #assert title in res
        #res = res.click(title)
        #assert '%s - Datasets' % title in res, res
        #main_div = self.main_div(res)
        #assert title in main_div, main_div.encode('utf8')

    def test_history(self):
        name = 'annakarenina'
        offset = url_for(controller='package', action='history', id=name)
        res = self.app.get(offset)
        assert 'History' in res
        assert 'Revisions' in res
        assert name in res

    def test_read_plugin_hook(self):
        plugins.load('test_package_controller_plugin')
        plugin = plugins.get_plugin('test_package_controller_plugin')
        name = u'annakarenina'
        offset = url_for(controller='package', action='read', id=name)
        res = self.app.get(offset)

        assert plugin.calls['read'] == 1, plugin.calls
        assert plugin.calls['after_show'] == 1, plugin.calls
        plugins.unload('test_package_controller_plugin')

    def test_resource_list(self):
        # TODO restore this test. It doesn't make much sense with the
        # present resource list design.
        name = 'annakarenina'
        cache_url = 'http://thedatahub.org/test_cache_url.csv'
        # add a cache_url to the first resource in the package
        context = {'model': model, 'session': model.Session, 'user': 'testsysadmin'}
        data = {'id': 'annakarenina'}
        pkg = get.package_show(context, data)
        pkg['resources'][0]['cache_url'] = cache_url
        # FIXME need to pretend to be called by the api
        context['api_version'] = 3
        update.package_update(context, pkg)
        # check that the cache url is included on the dataset view page
        offset = url_for(controller='package', action='read', id=name)
        res = self.app.get(offset)
        #assert '[cached]'in res
        #assert cache_url in res


class TestReadAtRevision(FunctionalTestCase, HtmlCheckMethods):

    @classmethod
    def setup_class(cls):
        cls.before = datetime.datetime(2010, 1, 1)
        cls.date1 = datetime.datetime(2011, 1, 1)
        cls.date2 = datetime.datetime(2011, 1, 2)
        cls.date3 = datetime.datetime(2011, 1, 3)
        cls.today = datetime.datetime.now()
        cls.pkg_name = u'testpkg'

        # create dataset
        rev = model.repo.new_revision()
        rev.timestamp = cls.date1
        pkg = model.Package(name=cls.pkg_name, title=u'title1')
        model.Session.add(pkg)
        model.setup_default_user_roles(pkg)
        model.repo.commit_and_remove()

        # edit dataset
        rev = model.repo.new_revision()
        rev.timestamp = cls.date2
        pkg = model.Package.by_name(cls.pkg_name)
        pkg.title = u'title2'
        pkg.add_tag_by_name(u'tag 2')
        pkg.extras = {'key2': u'value2'}
        model.repo.commit_and_remove()

        # edit dataset again
        rev = model.repo.new_revision()
        rev.timestamp = cls.date3
        pkg = model.Package.by_name(cls.pkg_name)
        pkg.title = u'title3'
        pkg.add_tag_by_name(u'tag3.')
        pkg.extras['key2'] = u'value3'
        model.repo.commit_and_remove()

        cls.offset = url_for(controller='package',
                             action='read',
                             id=cls.pkg_name)
        pkg = model.Package.by_name(cls.pkg_name)
        cls.revision_ids = [rev[0].id for rev in pkg.all_related_revisions[::-1]]
                        # revision order is reversed to be chronological

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_read_normally(self):
        res = self.app.get(self.offset, status=200)
        pkg_html = self.named_div('dataset', res)
        side_html = self.named_div('sidebar', res)
        print 'PKG', pkg_html
        assert 'title3' in res
        assert 'key2' in pkg_html
        assert 'value3' in pkg_html
        print 'SIDE', side_html
        assert 'tag3.' in side_html
        assert 'tag 2' in side_html

    def test_read_date1(self):
        offset = self.offset + self.date1.strftime('@%Y-%m-%d')
        res = self.app.get(offset, status=200)
        pkg_html = self.named_div('dataset', res)
        side_html = self.named_div('sidebar', res)
        assert 'title1' in res, res
        assert 'key2' not in pkg_html, pkg_html
        assert 'value3' not in pkg_html, pkg_html
        assert 'tag3.' not in side_html, side_html
        assert 'tag 2' not in side_html, side_html

    def test_read_date2(self):
        date2_plus_3h = self.date2 + datetime.timedelta(hours=3)
        offset = self.offset + date2_plus_3h.strftime('@%Y-%m-%d')
        res = self.app.get(offset, status=200)
        pkg_html = self.named_div('dataset', res)
        side_html = self.named_div('sidebar', res)
        print 'PKG', pkg_html
        assert 'title2' in res
        assert 'key2' in pkg_html
        assert 'value2' in pkg_html
        print 'SIDE', side_html
        assert 'tag3.' not in side_html
        assert 'tag 2' in side_html

    def test_read_date3(self):
        offset = self.offset + self.date3.strftime('@%Y-%m-%d-%H-%M')
        res = self.app.get(offset, status=200)
        pkg_html = self.named_div('dataset', res)
        side_html = self.named_div('sidebar', res)
        print 'PKG', pkg_html
        assert 'title3' in res
        assert 'key2' in pkg_html
        assert 'value3' in pkg_html
        print 'SIDE', side_html
        assert 'tag3.' in side_html
        assert 'tag 2' in side_html

    def test_read_date_before_created(self):
        offset = self.offset + self.before.strftime('@%Y-%m-%d')
        res = self.app.get(offset, status=404)

    def test_read_date_invalid(self):
        res = self.app.get(self.offset + self.date3.strftime('@%Y-%m'),
                           status=400)
        res = self.app.get(self.offset + self.date3.strftime('@%Y'),
                           status=400)
        res = self.app.get(self.offset + self.date3.strftime('@%Y@%m'),
                           status=400)

    def test_read_revision1(self):
        offset = self.offset + '@%s' % self.revision_ids[0]
        res = self.app.get(offset, status=200)
        main_html = self.main_div(res)
        pkg_html = self.named_div('dataset', res)
        side_html = self.named_div('sidebar', res)
        print 'MAIN', main_html
        assert 'This is an old revision of this dataset' in main_html
        assert 'at January 1, 2011, 00:00' in main_html
        self.check_named_element(main_html, 'a', 'href="/dataset/%s"' % self.pkg_name)
        print 'PKG', pkg_html
        assert 'title1' in res
        assert 'key2' not in pkg_html
        assert 'value3' not in pkg_html
        print 'SIDE', side_html
        assert 'tag3.' not in side_html
        assert 'tag 2' not in side_html

    def test_read_revision2(self):
        offset = self.offset + '@%s' % self.revision_ids[1]
        res = self.app.get(offset, status=200)
        main_html = self.main_div(res)
        pkg_html = self.named_div('dataset', res)
        side_html = self.named_div('sidebar', res)
        print 'MAIN', main_html
        assert 'This is an old revision of this dataset' in main_html
        assert 'at January 2, 2011, 00:00' in main_html
        self.check_named_element(main_html, 'a', 'href="/dataset/%s"' % self.pkg_name)
        print 'PKG', pkg_html
        assert 'title2' in res
        assert 'key2' in pkg_html
        assert 'value2' in pkg_html
        print 'SIDE', side_html
        assert 'tag3.' not in side_html
        assert 'tag 2' in side_html

    def test_read_revision3(self):
        offset = self.offset + '@%s' % self.revision_ids[2]
        res = self.app.get(offset, status=200)
        main_html = self.main_div(res)
        pkg_html = self.named_div('dataset', res)
        side_html = self.named_div('sidebar', res)
        print 'MAIN', main_html
        assert 'This is an old revision of this dataset' not in main_html
        assert 'This is the current revision of this dataset' in main_html
        assert 'at January 3, 2011, 00:00' in main_html
        self.check_named_element(main_html, 'a', 'href="/dataset/%s"' % self.pkg_name)
        print 'PKG', pkg_html
        assert 'title3' in res
        assert 'key2' in pkg_html
        assert 'value3' in pkg_html
        print 'SIDE', side_html
        assert 'tag3.' in side_html
        assert 'tag 2' in side_html

    def test_read_bad_revision(self):
        # this revision doesn't exist in the db
        offset = self.offset + '@ccab6798-1f4b-4a22-bcf5-462703aa4594'
        res = self.app.get(offset, status=404)

class TestEdit(TestPackageForm):
    editpkg_name = u'editpkgtest'

    @classmethod
    def setup_class(self):
        CreateTestData.create()

        self._reset_data()

    def setup(self):
        if not self.res:
            self.res = self.app.get(self.offset,extra_environ=self.extra_environ_admin)
        model.Session.remove()

    @classmethod
    def _reset_data(self):
        model.Session.remove()
        model.repo.rebuild_db()
        CreateTestData.create()
        CreateTestData.create_arbitrary(
            {'name':self.editpkg_name,
             'url':u'editpkgurl.com',
             'tags':[u'mytesttag'],
             'resources':[{'url':u'url escape: & umlaut: \xfc quote: "',
                          'description':u'description escape: & umlaut: \xfc quote "',
                          }],
             'admins':[u'testadmin'],
             })

        self.editpkg = model.Package.by_name(self.editpkg_name)
        self.pkgid = self.editpkg.id
        self.offset = url_for(controller='package', action='edit', id=self.editpkg_name)

        self.editpkg = model.Package.by_name(self.editpkg_name)
        self.admin = model.User.by_name(u'testsysadmin')

        self.extra_environ_admin = {'REMOTE_USER': self.admin.name.encode('utf8')}
        self.extra_environ_russianfan = {'REMOTE_USER': 'russianfan'}
        self.res = None #get's refreshed by setup
        model.Session.remove()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_edit_basic(self):
        # just the absolute basics
        try:
            self.res = self.app.get(self.offset,extra_environ=self.extra_environ_admin)
            assert 'Edit - Datasets' in self.res, self.res
            new_name = u'new-name'
            new_title = u'New Title'
            fv = self.res.forms['dataset-edit']
            prefix = ''
            fv[prefix + 'name'] = new_name
            fv[prefix + 'title'] = new_title
            res = fv.submit('save',extra_environ=self.extra_environ_admin)
            # get redirected ...
            res = res.follow()
            offset = url_for(controller='package', action='read', id=new_name)
            res = self.app.get(offset)
            assert '%s - Datasets' % new_title in res, res
            pkg = model.Package.by_name(new_name)
            assert pkg
            assert pkg.title == new_title
        finally:
            self._reset_data()

    def test_edit(self):
        # just the key fields
        try:
            self.res = self.app.get(self.offset,extra_environ=self.extra_environ_admin)
            assert 'Edit - Datasets' in self.res, self.res
            assert self.editpkg.notes in self.res

            new_name = u'new-name'
            new_title = u'A Short Description of this Dataset'
            newurl = u'http://www.editpkgnewurl.com'
            new_download_url = newurl + u'/download/'
            newlicense_id = u'cc-by'
            newversion = u'0.9b'
            fv = self.res.forms['dataset-edit']
            prefix = ''
            fv[prefix + 'name'] = new_name
            fv[prefix + 'title'] =  new_title
            fv[prefix + 'url'] =  newurl
            #fv[prefix + 'resources__0__url'] =  new_download_url
            fv[prefix + 'license_id'] =  newlicense_id
            fv[prefix + 'version'] = newversion
            res = fv.submit('save',extra_environ=self.extra_environ_admin)
            # get redirected ...
            res = res.follow()
            model.Session.remove()
            offset = url_for(controller='package', action='read', id=new_name)
            res = self.app.get(offset)
            assert '%s - Datasets' % new_title in res, res
            pkg = model.Package.by_name(new_name)
            assert pkg.title == new_title
            assert pkg.url == newurl
            #assert pkg.resources[0].url == new_download_url
            assert pkg.version == newversion
            assert newlicense_id == pkg.license.id
        finally:
            self._reset_data()

    def test_edit_basic_pkg_by_id(self):
        try:
            pkg = model.Package.by_name(u'editpkgtest')
            offset = url_for(controller='package', action='edit', id=pkg.id)
            res = self.app.get(offset, extra_environ=self.extra_environ_admin)
            #assert res.body == self.res.body, self.diff_responses(res, self.res)
            assert 'Edit - Datasets' in res, res
            assert pkg.name in res
            new_name = u'new-name'
            new_title = u'A Short Description of this Dataset'
            fv = self.res.forms['dataset-edit']
            prefix = ''
            fv[prefix + 'name'] = new_name
            fv[prefix + 'title'] =  new_title
            res = fv.submit('save', extra_environ=self.extra_environ_admin)
            # get redirected ...
            res = res.follow()
            offset = url_for(controller='package', action='read', id=new_name)
            res = self.app.get(offset)
            assert '%s - Datasets' % new_title in res, res
            pkg = model.Package.by_name(new_name)
            assert pkg
        finally:
            self._reset_data()

    def test_edit_2_not_groups(self):
        # not allowed to edit groups for now
        prefix = 'Dataset-%s-' % self.pkgid
        fv = self.res.forms['dataset-edit']
        assert not fv.fields.has_key(prefix + 'groups')

    def test_edit_2_tags_and_groups(self):
        # testing tag updating
        newtagnames = [u'russian', u'tolstoy', u'superb book']
        newtags = newtagnames
        tagvalues = ','.join(newtags)
        fv = self.res.forms['dataset-edit']
        prefix = ''
        fv[prefix + 'tag_string'] = tagvalues
        exp_log_message = 'test_edit_2: making some changes'
        fv['log_message'] =  exp_log_message
        res = fv.submit('save', extra_environ=self.extra_environ_admin)
        # get redirected ...
        res = res.follow()
        assert '%s - Datasets' % self.editpkg_name in res
        pkg = model.Package.by_name(self.editpkg.name)
        assert len(pkg.get_tags()) == len(newtagnames)
        outtags = [ tag.name for tag in pkg.get_tags() ]
        for tag in newtags:
            assert tag in outtags
        rev = model.Revision.youngest(model.Session)
        assert rev.author == self.admin.name
        assert rev.message == exp_log_message

    def test_redirect_after_edit_using_param(self):
        return_url = 'http://random.site.com/dataset/<NAME>?test=param'
        # It's useful to know that this url encodes to:
        # 'http%3A%2F%2Frandom.site.com%2Fdataset%2F%3CNAME%3E%3Ftest%3Dparam'
        expected_redirect = return_url
        self._check_redirect(return_url, expected_redirect,
                             pkg_name_to_edit=self.editpkg_name, extra_environ=self.extra_environ_admin)

    def test_redirect_after_edit_using_config(self):
        return_url = '' # redirect comes from test.ini setting
        expected_redirect = config['package_edit_return_url']
        self._check_redirect(return_url, expected_redirect,
                             pkg_name_to_edit=self.editpkg_name, extra_environ=self.extra_environ_admin)

    def test_edit_all_fields(self):
        try:
            # Create new item
            rev = model.repo.new_revision()
            pkg_name = u'new_editpkgtest'
            pkg = model.Package(name=pkg_name)
            pkg.title = u'This is a Test Title'
            pkg.url = u'editpkgurl.com'
            pr1 = model.Resource(url=u'editpkgurl1',
                  format=u'plain text', description=u'Full text',
                  hash=u'123abc',)
            pr2 = model.Resource(url=u'editpkgurl2',
                  format=u'plain text2', description=u'Full text2',
                  hash=u'456abc',)
            pkg.resources.append(pr1)
            pkg.resources.append(pr2)
            pkg.notes= u'this is editpkg'
            pkg.version = u'2.2'
            t1 = model.Tag(name=u'one')
            t2 = model.Tag(name=u'two words')
            pkg.add_tags([t1, t2])
            pkg.state = model.State.DELETED
            pkg.license_id = u'other-open'
            extras = {'key1':'value1', 'key2':'value2', 'key3':'value3'}
            for key, value in extras.items():
                pkg.extras[unicode(key)] = unicode(value)
            for obj in [pkg, t1, t2, pr1, pr2]:
                model.Session.add(obj)
            model.repo.commit_and_remove()
            pkg = model.Package.by_name(pkg_name)
            model.setup_default_user_roles(pkg, [self.admin])
            model.repo.commit_and_remove()

            # Edit it
            offset = url_for(controller='package', action='edit', id=pkg.name)
            res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER':'testsysadmin'})
            assert 'Edit - Datasets' in res, res

            # Check form is correctly filled
            pkg = model.Package.by_name(pkg_name)
            self.check_form_filled_correctly(res, pkg=pkg, log_message='')

            # Amend form
            name = u'test_name'
            title = u'Test Title'
            version = u'1.1'
            url = u'http://something.com/somewhere.zip'
            resources = ((u'http://something.com/somewhere-else.xml', u'xml', u'Best', u'hash1', 'alt'),
                         (u'http://something.com/somewhere-else2.xml', u'xml2', u'Best2', u'hash2', 'alt'),
                         )
            assert len(resources[0]) == 5
            notes = u'Very important'
            license_id = u'odc-by'
            state = model.State.ACTIVE
            tags = (u'tag1', u'tag2', u'tag 3')
            tags_txt = u','.join(tags)
            extra_changed = 'key1', self.value1 + ' CHANGED', False
            extra_new = 'newkey', 'newvalue', False
            log_message = 'This is a comment'
            assert not model.Package.by_name(name)
            fv = res.forms['dataset-edit']
            prefix = ''
            fv[prefix+'name'] = name
            fv[prefix+'title'] = title
            fv[prefix+'version'] = version
            fv[prefix+'url'] = url
            # TODO consider removing this test entirely, or hardcoding column names
            #for res_index, resource in enumerate(resources):
            #    for field_index, res_field in enumerate(model.Resource.get_columns()):
            #        fv[prefix+'resources__%s__%s' % (res_index, res_field)] = resource[field_index]
            fv[prefix+'notes'] = notes
            fv[prefix+'license_id'] = license_id
            fv[prefix+'tag_string'] = tags_txt
            fv[prefix+'state'] = state
            fv[prefix+'extras__0__value'] = extra_changed[1].encode('utf8')
            fv[prefix+'extras__3__key'] = extra_new[0].encode('utf8')
            fv[prefix+'extras__3__value'] = extra_new[1].encode('utf8')
            fv[prefix+'extras__2__deleted'] = True
            fv['log_message'] = log_message

            extras = (('key2', extras['key2'], False),
                       extra_changed,
                       extra_new,
                       ('key3', extras['key3'], True))

            res = fv.submit('save', extra_environ={'REMOTE_USER':'testsysadmin'})

            # Check dataset page
            assert not 'Error' in res, res

            # Check dataset object
            pkg = model.Package.by_name(name)
            assert pkg.name == name
            assert pkg.title == title
            assert pkg.version == version
            assert pkg.url == url
            # TODO consider removing this test entirely, or hardcoding column names
            #for res_index, resource in enumerate(resources):
            #    for field_index, res_field in enumerate(model.Resource.get_columns()):
            #        assert getattr(pkg.resources[res_index], res_field) == resource[field_index]
            assert pkg.notes == notes
            assert pkg.license.id == license_id
            saved_tagnames = [str(tag.name) for tag in pkg.get_tags()]
            saved_tagnames.sort()
            expected_tagnames = list(tags)
            expected_tagnames.sort()
            assert saved_tagnames == expected_tagnames
            assert pkg.state == state
            assert len(pkg.extras) == len([extra for extra in extras if not extra[-1]])
            for key, value, deleted in extras:
                if not deleted:
                    assert pkg.extras[key] == value

            # for some reason environ['REMOTE_ADDR'] is undefined
            rev = model.Revision.youngest(model.Session)
            assert rev.author == 'testsysadmin', rev.author
            assert rev.message == log_message
            # TODO: reinstate once fixed in code
            exp_log_message = u'Creating dataset %s' % name
            #assert rev.message == exp_log_message
        finally:
            self._reset_data()

    # NB: Cannot test resources now because it is all javascript!
##    def test_edit_invalid_resource(self):
##        try:
##            # Create new dataset
##            pkg_name = u'test_res'
##            CreateTestData.create_arbitrary({'name': pkg_name,
##                                             'resources': [{'url': '1.pdf'}]})

##            # Edit it
##            pkg = model.Package.by_name(pkg_name)
##            offset = url_for(controller='package', action='edit', id=pkg.name)
##            res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER':'testadmin'})
##            assert 'Edit - Datasets' in res, res

##            pkg = model.Package.by_name(pkg_name)

##            # Amend form
##            fv = res.forms['dataset-edit']

##            fv['resources__0__size'] = 'abc'
##            res = fv.submit('save', extra_environ={'REMOTE_USER':'testadmin'})

##            # Check dataset page
##            assert 'Errors in form' in res, res
##            assert 'Package resource(s) invalid' in res, res
##            assert 'Resource 1' in res, res
##        finally:
##            self._reset_data()

    def test_edit_bad_log_message(self):
        fv = self.res.forms['dataset-edit']
        prefix = ''
        fv['log_message'] = u'Free enlargements: http://drugs.com/' # spam
        res = fv.submit('save', extra_environ=self.extra_environ_admin)
        assert 'Error' in res, res
        self.check_tag(res, '<form', 'has-errors')
        assert 'No links are allowed' in res, res

    def test_edit_bad_name(self):
        fv = self.res.forms['dataset-edit']
        prefix = ''
        fv[prefix + 'name'] = u'a' # invalid name
        res = fv.submit('save', extra_environ=self.extra_environ_admin)
        assert 'Error' in res, res
        assert 'Name must be at least 2 characters long' in res, res
        # Ensure there is an error at the top of the form and by the field
        self._assert_form_errors(res)


    def test_edit_plugin_hook(self):
        # just the absolute basics
        try:
            plugins.load('test_package_controller_plugin')
            plugin = plugins.get_plugin('test_package_controller_plugin')
            res = self.app.get(self.offset, extra_environ=self.extra_environ_admin)
            new_name = u'new-name'
            new_title = u'New Title'
            fv = res.forms['dataset-edit']
            prefix = ''
            fv[prefix + 'name'] = new_name
            fv[prefix + 'title'] = new_title
            res = fv.submit('save', extra_environ=self.extra_environ_admin)
            # get redirected ...
            assert plugin.calls['edit'] == 1, plugin.calls
            plugins.unload('test_package_controller_plugin')
        finally:
            self._reset_data()

    def test_after_update_plugin_hook(self):
        # just the absolute basics
        try:
            plugins.load('test_package_controller_plugin')
            plugin = plugins.get_plugin('test_package_controller_plugin')
            res = self.app.get(self.offset, extra_environ=self.extra_environ_admin)
            new_name = u'new-name'
            new_title = u'New Title'
            fv = res.forms['dataset-edit']
            prefix = ''
            fv[prefix + 'name'] = new_name
            fv[prefix + 'title'] = new_title
            res = fv.submit('save', extra_environ=self.extra_environ_admin)
            # get redirected ...
            assert plugin.calls['after_update'] == 1, plugin.calls
            assert plugin.calls['after_create'] == 0, plugin.calls
            plugins.unload('test_package_controller_plugin')
        finally:
            self._reset_data()

    def test_edit_700_groups_add(self):
        try:
            pkg = model.Package.by_name(u'editpkgtest')
            grp = model.Group.by_name(u'roger')
            assert len(pkg.get_groups()) == 0
            offset = url_for(controller='package', action='edit', id=pkg.name)

            res = self.app.get(offset, extra_environ=self.extra_environ_admin)
            prefix = ''
            field_name = prefix + "groups__0__id"
            assert field_name in res
            fv = res.forms['dataset-edit']
            fv[prefix + 'groups__0__id'] = grp.id
            res = fv.submit('save', extra_environ=self.extra_environ_admin)
            res = res.follow()
            pkg = model.Package.by_name(u'editpkgtest')
            assert len(pkg.get_groups()) == 1, pkg.get_groups()
            assert 'roger' in res, res
        finally:
            self._reset_data()

    def test_edit_700_groups_remove(self):
        try:
            pkg = model.Package.by_name(u'editpkgtest')
            assert len(pkg.get_groups()) == 0
            grp = model.Group.by_name(u'roger')
            model.repo.new_revision()
            model.Session.add(model.Member(table_id=pkg.id, table_name='package', group=grp))
            model.repo.commit_and_remove()
            pkg = model.Package.by_name(u'editpkgtest')
            assert len(pkg.get_groups()) == 1
            offset = url_for(controller='package', action='edit', id=pkg.name)
            res = self.app.get(offset, extra_environ=self.extra_environ_admin)
            prefix = ''
            field_name = prefix + "groups__0__id"
            fv = res.forms['dataset-edit']
            print field_name
            fv[field_name] = False
            res = fv.submit('save', extra_environ=self.extra_environ_admin)
            model.repo.commit_and_remove()
            pkg = model.Package.by_name(u'editpkgtest')
            assert len(pkg.get_groups()) == 0
        finally:
            self._reset_data()

    def test_edit_404(self):
        self.offset = url_for(controller='package', action='edit', id='random_name')
        self.res = self.app.get(self.offset, status=404)

    def test_edit_indexerror(self):
        bad_solr_url = 'http://127.0.0.1/badsolrurl'
        solr_url = SolrSettings.get()[0]
        try:
            SolrSettings.init(bad_solr_url)

            fv = self.res.forms['dataset-edit']
            fv['log_message'] = u'Test log message'
            res = fv.submit('save', status=500, extra_environ=self.extra_environ_admin)
            assert 'Unable to update search index' in res, res
        finally:
            SolrSettings.init(solr_url)

    def test_edit_pkg_with_relationships(self):
        # 1786
        try:
            # add a relationship to a package
            pkg = model.Package.by_name(self.editpkg_name)
            anna = model.Package.by_name(u'annakarenina')
            model.repo.new_revision()
            pkg.add_relationship(u'depends_on', anna)
            model.repo.commit_and_remove()

            # check relationship before the test
            rels = model.Package.by_name(self.editpkg_name).get_relationships()
            assert_equal(str(rels), '[<*PackageRelationship editpkgtest depends_on annakarenina>]')

            # edit the package
            self.offset = url_for(controller='package', action='edit', id=self.editpkg_name)
            self.res = self.app.get(self.offset, extra_environ=self.extra_environ_admin)
            fv = self.res.forms['dataset-edit']
            fv['title'] = u'New Title'
            res = fv.submit('save')

            # check relationship still exists
            rels = model.Package.by_name(self.editpkg_name).get_relationships()
            assert_equal(str(rels), '[<*PackageRelationship editpkgtest depends_on annakarenina>]')

        finally:
            self._reset_data()


class TestDelete(TestPackageForm):

    pkg_names = []

    @classmethod
    def setup_class(self):
        model.repo.init_db()
        CreateTestData.create()
        CreateTestData.create_test_user()

        self.admin = model.User.by_name(u'testsysadmin')

        self.extra_environ_admin = {'REMOTE_USER': self.admin.name.encode('utf8')}
        self.extra_environ_tester = {'REMOTE_USER': 'tester'}

    @classmethod
    def teardown_class(self):
        self.purge_packages(self.pkg_names)
        model.repo.rebuild_db()

    def test_delete(self):
        plugins.load('test_package_controller_plugin')
        plugin = plugins.get_plugin('test_package_controller_plugin')

        offset = url_for(controller='package', action='delete',
                id='warandpeace')
        # Since organizations, any owned dataset can be edited/deleted by any
        # user
        self.app.post(offset, extra_environ=self.extra_environ_tester)

        self.app.post(offset, extra_environ=self.extra_environ_admin)

        assert model.Package.get('warandpeace').state == u'deleted'

        assert plugin.calls['delete'] == 2
        assert plugin.calls['after_delete'] == 2
        plugins.unload('test_package_controller_plugin')


class TestNew(TestPackageForm):
    pkg_names = []

    @classmethod
    def setup_class(self):
        model.repo.init_db()
        CreateTestData.create_test_user()
#        self.admin = model.User.by_name(u'russianfan')

#        self.extra_environ_admin = {'REMOTE_USER': self.admin.name.encode('utf8')}
        self.extra_environ_tester = {'REMOTE_USER': 'tester'}

    @classmethod
    def teardown_class(self):
        self.purge_packages(self.pkg_names)
        model.repo.rebuild_db()

    def test_new_with_params_1(self):
        offset = url_for(controller='package', action='new',
                url='http://xxx.org', name='xxx.org')
        res = self.app.get(offset, extra_environ=self.extra_environ_tester)
        form = res.forms['dataset-edit']
        assert_equal(form['url'].value, 'http://xxx.org')
        assert_equal(form['name'].value, 'xxx.org')

    def test_new_without_resource(self):
        # new dataset
        prefix = ''
        name = u'test_no_res'
        offset = url_for(controller='package', action='new')
        res = self.app.get(offset, extra_environ=self.extra_environ_tester)
        fv = res.forms['dataset-edit']
        fv[prefix+'name'] = name
        # submit
        self.pkg_names.append(name)
        res = fv.submit('save', extra_environ=self.extra_environ_tester)

        # check dataset page
        assert not 'Error' in res, res
        res = res.follow()
        res1 = self.main_div(res).replace('</strong>', '')
        assert '<td><a href="">' not in res1, res1

        # check object created
        pkg = model.Package.by_name(name)
        assert pkg
        assert pkg.name == name
        assert not pkg.resources, pkg.resources

    def test_new(self):
        assert not model.Package.by_name(u'annakarenina')
        offset = url_for(controller='package', action='new')
        res = self.app.get(offset, extra_environ=self.extra_environ_tester)
        assert 'Add - Datasets' in res
        fv = res.forms['dataset-edit']
        prefix = ''
        fv[prefix + 'name'] = 'annakarenina'
        self.pkg_names.append('annakarenina')
        res = fv.submit('save', extra_environ=self.extra_environ_tester)
        assert not 'Error' in res, res

    def test_new_bad_name(self):
        offset = url_for(controller='package', action='new', id=None)
        res = self.app.get(offset, extra_environ=self.extra_environ_tester)
        assert 'Add - Datasets' in res
        fv = res.forms['dataset-edit']
        prefix = ''
        fv[prefix + 'name'] = u'a' # invalid name
        self.pkg_names.append('a')
        res = fv.submit('save', extra_environ=self.extra_environ_tester)
        assert 'Error' in res, res
        assert 'Name must be at least 2 characters long' in res, res
        self._assert_form_errors(res)

    def test_new_no_name(self):
        offset = url_for(controller='package', action='new', id=None)
        res = self.app.get(offset, extra_environ=self.extra_environ_tester)
        assert 'Add - Datasets' in res
        fv = res.forms['dataset-edit']
        prefix = ''
        # don't set a name
        res = fv.submit('save', extra_environ=self.extra_environ_tester)
        assert 'Error' in res, res
        assert 'URL: Missing value' in res, res
        self._assert_form_errors(res)

    def test_redirect_after_new_using_param(self):
        return_url = 'http://random.site.com/dataset/<NAME>?test=param'
        # It's useful to know that this url encodes to:
        # 'http%3A%2F%2Frandom.site.com%2Fdataset%2F%3CNAME%3E%3Ftest%3Dparam'
        expected_redirect = return_url
        self._check_redirect(return_url, expected_redirect,
                             pkg_name_to_edit='', extra_environ=self.extra_environ_tester)

    def test_redirect_after_new_using_config(self):
        return_url = '' # redirect comes from test.ini setting
        expected_redirect = config['package_new_return_url']
        self._check_redirect(return_url, expected_redirect,
                             pkg_name_to_edit='', extra_environ=self.extra_environ_tester)

    def test_new_all_fields(self):
        name = u'test_name2'
        title = u'Test Title'
        version = u'1.1'
        url = u'http://something.com/somewhere.zip'
        download_url = u'http://something.com/somewhere-else.zip'
        notes = u'Very important'
        license_id = u'odc-by'
        tags = (u'tag1', u'tag2.', u'tag 3', u'SomeCaps')
        tags_txt = u','.join(tags)
        extras = {self.key1:self.value1, 'key2':'value2', 'key3':'value3'}
        log_message = 'This is a comment'
        assert not model.Package.by_name(name)
        offset = url_for(controller='package', action='new')
        res = self.app.get(offset, extra_environ=self.extra_environ_tester)
        assert 'Add - Datasets' in res
        fv = res.forms['dataset-edit']
        prefix = ''
        fv[prefix+'name'] = name
        fv[prefix+'title'] = title
        fv[prefix+'version'] = version
        fv[prefix+'url'] = url
        #fv[prefix+'resources__0__url'] = download_url
        #fv[prefix+'resources__0__description'] = u'description escape: & umlaut: \xfc quote "'.encode('utf8')
        fv[prefix+'notes'] = notes
        fv[prefix+'license_id'] = license_id
        fv[prefix+'tag_string'] = tags_txt
        for i, extra in enumerate(sorted(extras.items())):
            fv[prefix+'extras__%s__key' % i] = extra[0].encode('utf8')
            fv[prefix+'extras__%s__value' % i] = extra[1].encode('utf8')
        fv['log_message'] = log_message
        # Submit
        fv = res.forms['dataset-edit']
        self.pkg_names.append(name)
        res = fv.submit('save', extra_environ=self.extra_environ_tester)

        # Check dataset page
        assert not 'Error' in res, res

        # Check dataset object
        pkg = model.Package.by_name(name)
        assert pkg.name == name
        assert pkg.title == title
        assert pkg.version == version
        assert pkg.url == url
        #assert pkg.resources[0].url == download_url
        assert pkg.notes == notes
        assert pkg.license.id == license_id
        saved_tagnames = [str(tag.name) for tag in pkg.get_tags()]
        saved_tagnames.sort()
        expected_tagnames = sorted(tags)
        assert saved_tagnames == expected_tagnames, '%r != %r' % (saved_tagnames, expected_tagnames)
        saved_groupnames = [str(group.name) for group in pkg.get_groups()]
        assert len(pkg.extras) == len(extras)
        for key, value in extras.items():
            assert pkg.extras[key] == value

        # for some reason environ['REMOTE_ADDR'] is undefined
        rev = model.Revision.youngest(model.Session)
        assert rev.author == 'tester'
        assert rev.message == log_message
        # TODO: reinstate once fixed in code
        exp_log_message = u'Creating dataset %s' % name
        # assert rev.message == exp_log_message

    def test_new_existing_name(self):
        # test creating a dataset with an existing name results in error'
        # create initial dataset
        pkgname = u'testpkg'
        pkgtitle = u'mytesttitle'
        assert not model.Package.by_name(pkgname)
        offset = url_for(controller='package', action='new', id=None)
        res = self.app.get(offset, extra_environ=self.extra_environ_tester)
        assert 'Add - Datasets' in res
        fv = res.forms['dataset-edit']
        prefix = ''
        fv[prefix + 'name'] = pkgname
        self.pkg_names.append(pkgname)
        res = fv.submit('save', extra_environ=self.extra_environ_tester)
        assert not 'Error' in res, res
        assert model.Package.by_name(pkgname)
        # create duplicate dataset
        res = self.app.get(offset, extra_environ=self.extra_environ_tester)
        assert 'Add - Datasets' in res
        fv = res.forms['dataset-edit']
        fv[prefix+'name'] = pkgname
        fv[prefix+'title'] = pkgtitle
        res = fv.submit('save', extra_environ=self.extra_environ_tester)
        assert 'Error' in res, res
        assert 'That URL is already in use.' in res, res
        self._assert_form_errors(res)

    def test_new_plugin_hook(self):
        plugins.load('test_package_controller_plugin')
        plugin = plugins.get_plugin('test_package_controller_plugin')
        offset = url_for(controller='package', action='new')
        res = self.app.get(offset, extra_environ=self.extra_environ_tester)
        new_name = u'plugged'
        fv = res.forms['dataset-edit']
        prefix = ''
        fv[prefix + 'name'] = new_name
        res = fv.submit('save', extra_environ=self.extra_environ_tester)
        # get redirected ...
        assert plugin.calls['edit'] == 0, plugin.calls
        assert plugin.calls['create'] == 1, plugin.calls
        plugins.unload('test_package_controller_plugin')

    def test_after_create_plugin_hook(self):
        plugins.load('test_package_controller_plugin')
        plugin = plugins.get_plugin('test_package_controller_plugin')
        offset = url_for(controller='package', action='new')
        res = self.app.get(offset, extra_environ=self.extra_environ_tester)
        new_name = u'plugged2'
        fv = res.forms['dataset-edit']
        prefix = ''
        fv[prefix + 'name'] = new_name
        res = fv.submit('save', extra_environ=self.extra_environ_tester)
        # get redirected ...
        assert plugin.calls['after_update'] == 0, plugin.calls
        assert plugin.calls['after_create'] == 1, plugin.calls

        assert plugin.id_in_dict
        plugins.unload('test_package_controller_plugin')

    def test_new_indexerror(self):
        bad_solr_url = 'http://127.0.0.1/badsolrurl'
        solr_url = SolrSettings.get()[0]
        try:
            SolrSettings.init(bad_solr_url)
            new_package_name = u'new-package-missing-solr'

            offset = url_for(controller='package', action='new')
            res = self.app.get(offset, extra_environ=self.extra_environ_tester)
            fv = res.forms['dataset-edit']
            fv['name'] = new_package_name

            # this package shouldn't actually be created but
            # add it to the list to purge just in case
            self.pkg_names.append(new_package_name)

            res = fv.submit('save', status=500, extra_environ=self.extra_environ_tester)
            assert 'Unable to add package to search index' in res, res
        finally:
            SolrSettings.init(solr_url)

    def test_change_locale(self):
        offset = url_for(controller='package', action='new')
        res = self.app.get(offset, extra_environ=self.extra_environ_tester)

        res = self.app.get('/de/dataset/new', extra_environ=self.extra_environ_tester)
        try:
            assert 'Datensatz' in res.body, res.body
        finally:
            self.clear_language_setting()

class TestSearch(TestPackageForm):
    pkg_names = []

    @classmethod
    def setup_class(self):
        model.repo.init_db()

    @classmethod
    def teardown_class(self):
        self.purge_packages(self.pkg_names)
        model.repo.rebuild_db()

    def test_search_plugin_hooks(self):
        plugins.load('test_package_controller_plugin')
        plugin = plugins.get_plugin('test_package_controller_plugin')
        offset = url_for(controller='package', action='search')
        res = self.app.get(offset)
        # get redirected ...
        assert plugin.calls['before_search'] == 1, plugin.calls
        assert plugin.calls['after_search'] == 1, plugin.calls
        plugins.unload('test_package_controller_plugin')

class TestNewPreview(TestPackageBase):
    pkgname = u'testpkg'
    pkgtitle = u'mytesttitle'

    @classmethod
    def setup_class(self):
        pass
        model.repo.init_db()

    @classmethod
    def teardown_class(self):
        self.purge_packages([self.pkgname])
        model.repo.rebuild_db()

class TestNonActivePackages(TestPackageBase):

    @classmethod
    def setup_class(self):
        CreateTestData.create()
        self.non_active_name = u'test_nonactive'
        pkg = model.Package(name=self.non_active_name)
        model.repo.new_revision()
        model.Session.add(pkg)
        model.repo.commit_and_remove()

        pkg = model.Session.query(model.Package).filter_by(name=self.non_active_name).one()
        admin = model.User.by_name(u'joeadmin')
        model.setup_default_user_roles(pkg, [admin])
        model.repo.commit_and_remove()

        model.repo.new_revision()
        pkg = model.Session.query(model.Package).filter_by(name=self.non_active_name).one()
        pkg.delete() # becomes non active
        model.repo.commit_and_remove()


    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_read(self):
        offset = url_for(controller='package', action='read', id=self.non_active_name)
        res = self.app.get(offset, status=[302, 401])


    def test_read_as_admin(self):
        offset = url_for(controller='package', action='read', id=self.non_active_name)
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER':'testsysadmin'})


class TestRevisions(TestPackageBase):
    @classmethod
    def setup_class(cls):
        model.Session.remove()
        model.repo.init_db()
        cls.name = u'revisiontest1'

        # create pkg
        cls.notes = [u'Written by Puccini', u'Written by Rossini', u'Not written at all', u'Written again', u'Written off']
        rev = model.repo.new_revision()
        cls.pkg1 = model.Package(name=cls.name)
        cls.pkg1.notes = cls.notes[0]
        model.Session.add(cls.pkg1)
        model.setup_default_user_roles(cls.pkg1)
        model.repo.commit_and_remove()

        # edit pkg
        for i in range(5)[1:]:
            rev = model.repo.new_revision()
            pkg1 = model.Package.by_name(cls.name)
            pkg1.notes = cls.notes[i]
            model.repo.commit_and_remove()

        cls.pkg1 = model.Package.by_name(cls.name)
        cls.revision_ids = [rev[0].id for rev in cls.pkg1.all_related_revisions]
                           # revision ids are newest first
        cls.revision_timestamps = [rev[0].timestamp for rev in cls.pkg1.all_related_revisions]
        cls.offset = url_for(controller='package', action='history', id=cls.pkg1.name)

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_0_read_history(self):
        res = self.app.get(self.offset)
        main_res = self.main_div(res)
        assert self.pkg1.name in main_res, main_res
        assert 'radio' in main_res, main_res
        latest_rev = self.pkg1.all_revisions[0]
        oldest_rev = self.pkg1.all_revisions[-1]
        first_radio_checked_html = '<input checked="checked" id="selected1_%s"' % latest_rev.revision_id
        assert first_radio_checked_html in main_res, '%s %s' % (first_radio_checked_html, main_res)
        last_radio_checked_html = '<input checked="checked" id="selected2_%s"' % oldest_rev.revision_id
        assert last_radio_checked_html in main_res, '%s %s' % (last_radio_checked_html, main_res)

    def test_1_do_diff(self):
        res = self.app.get(self.offset)
        form = res.forms['dataset-revisions']
        res = form.submit()
        res = res.follow()
        main_res = self.main_div(res)
        assert 'form-errors' not in main_res.lower(), main_res
        assert 'Revision Differences' in main_res, main_res
        assert self.pkg1.name in main_res, main_res
        assert '<tr><td>notes</td><td><pre>- Written by Puccini\n+ Written off</pre></td></tr>' in main_res, main_res

    def test_2_atom_feed(self):
        offset = "%s?format=atom" % self.offset
        res = self.app.get(offset)
        assert '<feed' in res, res
        assert 'xmlns="http://www.w3.org/2005/Atom"' in res, res
        assert '</feed>' in res, res

    def test_3_history_revision_link(self):
        res = self.app.get(self.offset)
        res = res.click('%s' % self.revision_ids[2][:4])
        main_res = self.main_div(res)
        assert 'Revision: %s' % self.revision_ids[2] in main_res

    def test_4_history_revision_package_link(self):
        res = self.app.get(self.offset)
        url = str(self.revision_timestamps[1])[-6:]
        res = res.click(href=url)
        main_html = self.main_div(res)
        assert 'This is an old revision of this dataset' in main_html


class TestMarkdownHtmlWhitelist(TestPackageForm):

    pkg_name = u'markdownhtmlwhitelisttest'
    pkg_notes = u'''
<table width="100%" border="1">
<tr>
<td rowspan="2"><b>Description</b></td>
<td rowspan="2"><b>Documentation</b></td>

<td colspan="2"><b><center>Data -- Pkzipped</center></b> </td>
</tr>
<tr>
<td><b>SAS .tpt</b></td>
<td><b>ASCII CSV</b> </td>
</tr>
<tr>
<td><b>Overview</b></td>
<td><A HREF="http://www.nber.org/patents/subcategories.txt">subcategory.txt</A></td>
<td colspan="2"><center>--</center></td>
</tr>
<script><!--
alert('Hello world!');
//-->
</script>

'''

    def setup(self):
        model.Session.remove()
        model.repo.init_db()
        rev = model.repo.new_revision()
        CreateTestData.create_arbitrary(
            {'name':self.pkg_name,
             'notes':self.pkg_notes,
             'admins':[u'testadmin']}
            )
        self.pkg = model.Package.by_name(self.pkg_name)
        self.pkg_id = self.pkg.id

        offset = url_for(controller='package', action='read', id=self.pkg_name)
        self.res = self.app.get(offset)

    def teardown(self):
        model.repo.rebuild_db()

    def test_markdown_html_whitelist(self):
        self.body = str(self.res)
        self.fail_if_fragment('<table width="100%" border="1">')
        self.fail_if_fragment('<td rowspan="2"><b>Description</b></td>')
        self.fail_if_fragment('<a href="http://www.nber.org/patents/subcategories.txt" target="_blank" rel="nofollow">subcategory.txt</a>')
        self.fail_if_fragment('<td colspan="2"><center>--</center></td>')
        self.fail_if_fragment('<script>')

    def assert_fragment(self, fragment):
        assert fragment in self.body, (fragment, self.body)

    def fail_if_fragment(self, fragment):
        assert fragment not in self.body, (fragment, self.body)

class TestAutocomplete(PylonsTestCase, TestPackageBase):
    @classmethod
    def setup_class(cls):
        PylonsTestCase.setup_class()
        CreateTestData.create()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_package_autocomplete(self):
        query = 'a'
        res = self.app.get('/dataset/autocomplete?q=%s' % query)

        expected = ['A Wonderful Story (warandpeace)|warandpeace','annakarenina|annakarenina']
        received = sorted(res.body.split('\n'))
        assert expected == received

class TestResourceListing(TestPackageBase):
    @classmethod
    def setup_class(cls):

        CreateTestData.create()
        cls.tester_user = model.User.by_name(u'tester')
        cls.extra_environ_admin = {'REMOTE_USER': 'testsysadmin'}
        cls.extra_environ_tester = {'REMOTE_USER': 'tester'}
        cls.extra_environ_someone_else = {'REMOTE_USER': 'someone_else'}

        tests.call_action_api(cls.app, 'organization_create',
                                        name='test_org_2',
                                        apikey=cls.tester_user.apikey)

        tests.call_action_api(cls.app, 'package_create',
                                        name='crimeandpunishment',
                                        owner_org='test_org_2',
                                        apikey=cls.tester_user.apikey)

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_resource_listing_premissions_sysadmin(self):
        # sysadmin 200
         self.app.get('/dataset/resources/crimeandpunishment', extra_environ=self.extra_environ_admin, status=200)

    def test_resource_listing_premissions_auth_user(self):
        # auth user 200
         self.app.get('/dataset/resources/crimeandpunishment', extra_environ=self.extra_environ_tester, status=200)

    def test_resource_listing_premissions_non_auth_user(self):
        # non auth user 401
         self.app.get('/dataset/resources/crimeandpunishment', extra_environ=self.extra_environ_someone_else, status=[302,401])

    def test_resource_listing_premissions_not_logged_in(self):
        # not logged in 401
         self.app.get('/dataset/resources/crimeandpunishment', status=[302,401])

