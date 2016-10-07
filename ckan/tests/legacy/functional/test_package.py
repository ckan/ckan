# encoding: utf-8

import datetime

from ckan.common import config, c
from difflib import unified_diff
from nose.tools import assert_equal

from ckan.tests.legacy import *
import ckan.tests.legacy as tests
from ckan.tests.legacy.html_check import HtmlCheckMethods
from ckan.tests.legacy.pylons_controller import PylonsTestCase
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
            key_escaped = key
            value_escaped = value
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
        main_html = pkg_html = side_html = res.body
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
        main_html = pkg_html = side_html = res.body
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
        main_html = pkg_html = side_html = res.body
        print 'MAIN', main_html
        assert 'This is an old revision of this dataset' in main_html
        # It is not an old revision, but working that out is hard. The request
        # was for a particular revision, so assume it is old.
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

    def test_edit_2_not_groups(self):
        # not allowed to edit groups for now
        prefix = 'Dataset-%s-' % self.pkgid
        fv = self.res.forms['dataset-edit']
        assert not fv.fields.has_key(prefix + 'groups')


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


    def test_edit_404(self):
        self.offset = url_for(controller='package', action='edit', id='random_name')
        self.res = self.app.get(self.offset, status=404)


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
            res = fv.submit('save', extra_environ=self.extra_environ_admin)

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
        bad_solr_url = 'http://example.com/badsolrurl'
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
        res = self.app.get(offset, status=[404])


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

    def test_2_atom_feed(self):
        offset = "%s?format=atom" % self.offset
        res = self.app.get(offset)
        assert '<feed' in res, res
        assert 'xmlns="http://www.w3.org/2005/Atom"' in res, res
        assert '</feed>' in res, res



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
        # non auth user 403
         self.app.get('/dataset/resources/crimeandpunishment', extra_environ=self.extra_environ_someone_else, status=[403])

    def test_resource_listing_premissions_not_logged_in(self):
        # not logged in 403
         self.app.get('/dataset/resources/crimeandpunishment', status=[403])

