from ckan.tests import *
import ckan.model as model
import simplejson
import webhelpers

ACCESS_DENIED = [401,403]
def get_license_name(id):
    return model.Session.get(model.License, id).name


class TestRestController(TestController):

    @classmethod
    def setup_class(self):
        try:
            CreateTestData.delete()
        except:
            pass
        model.Session.remove()
        CreateTestData.create()
        model.Package(name=u'--')
        rev = model.repo.new_revision()
        model.repo.commit_and_remove()


    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    def setup(self):
        self.testvalues = {
            'name' : u'testpkg',
            'title': u'Some Title',
            'url': u'http://blahblahblah.mydomain',
            'download_url': u'http://blahblahblah.mydomain',
            'tags': u'russion novel',
            'license_id': u'4',
        }
        self.random_name = u'http://myrandom.openidservice.org/'
        self.user = model.User(name=self.random_name)
        model.Session.commit()
        self.extra_environ={ 'Authorization' : str(self.user.apikey) }
        model.Session.remove()


    def teardown(self):
        model.Session.remove()
        user = model.User.by_name(self.random_name)
        if user:
            user.purge()
        pkg = model.Package.by_name(self.testvalues['name'])
        if pkg:
            pkg.purge()
        model.Session.commit()
        model.Session.remove()

    def test_01_register_post_noauth(self):
        # Test Packages Register Post 401.
        offset = '/api/rest/package'
        postparams = '%s=1' % simplejson.dumps(self.testvalues)
        res = self.app.post(offset, params=postparams, status=ACCESS_DENIED)

    def test_01_entity_put_noauth(self):
        # Test Packages Entity Put 401.
        offset = '/api/rest/package/%s' % u'--'
        postparams = '%s=1' % simplejson.dumps(self.testvalues)
        res = self.app.post(offset, params=postparams, status=ACCESS_DENIED)

    def test_01_entity_delete_noauth(self):
        # Test Packages Entity Delete 401.
        offset = '/api/rest/package/%s' % u'annakarenina'
        res = self.app.delete(offset, status=ACCESS_DENIED)

    def test_02_list_package(self):
        # Test Packages Register Get 200.
        offset = '/api/rest/package'
        res = self.app.get(offset, status=[200])
        assert 'annakarenina' in res, res
        assert 'warandpeace' in res, res

    def test_02_list_tags(self):
        # Test Packages Register Get 200.
        offset = '/api/rest/tag'
        res = self.app.get(offset, status=[200])
        assert 'russian' in res, res
        assert 'tolstoy' in res, res

    def test_04_get_package(self):
        # Test Packages Register Get 200.
        offset = '/api/rest/package/annakarenina'
        res = self.app.get(offset, status=[200])
        assert 'annakarenina' in res, res
        assert '"license_id": 9' in res, res
        expected_license = '"license": "%s"' % get_license_name(9)
        assert expected_license in res, repr(res) + repr(expected_license)
        assert 'russian' in res, res
        assert 'tolstoy' in res, res
        

    def test_04_get_tag(self):
        # TODO document this one
        offset = '/api/rest/tag/tolstoy'
        res = self.app.get(offset, status=[200])
        assert 'annakarenina' in res, res
        assert not 'warandpeace' in res, res

    def test_05_get_404(self):
        # Test Package Entity Get 404.
        offset = '/api/rest/package/22222'
        res = self.app.get(offset, status=404)
        model.Session.remove()

    def test_06_create(self):
        # Test Packages Register Post 200.
        offset = '/api/rest/package'
        postparams = '%s=1' % simplejson.dumps(self.testvalues)
        res = self.app.post(offset, params=postparams, status=[200],
                extra_environ=self.extra_environ)
        model.Session.remove()
        pkg = model.Package.by_name(self.testvalues['name'])
        assert pkg
        assert pkg.title == self.testvalues['title'], pkg
        assert pkg.url == self.testvalues['url'], pkg
        assert pkg.license_id == int(self.testvalues['license_id']), pkg
        assert len(pkg.tags) == 2

        # Test Package Entity Get 200.
        offset = '/api/rest/package/%s' % self.testvalues['name']
        res = self.app.get(offset, status=[200])
        assert self.testvalues['name'] in res, res
        assert '"license_id": %s' % self.testvalues['license_id'] in res, res
        assert self.testvalues['tags'][0] in res, res
        assert self.testvalues['tags'][1] in res, res
        
        model.Session.remove()
        
        # Test Packages Register Post 409 (conflict - create duplicate package).
        offset = '/api/rest/package'
        postparams = '%s=1' % simplejson.dumps(self.testvalues)
        res = self.app.post(offset, params=postparams, status=[409],
                extra_environ=self.extra_environ)
        model.Session.remove()

    def _test_09_entity_put_404(self):
        # TODO: get this working again. At present returns 400
        # Test Package Entity Put 404.
        offset = '/api/rest/package/22222'
        postparams = '%s=1' % simplejson.dumps(self.testvalues)
        # res = self.app.post(offset, params=postparams, status=[404],
        #        extra_environ=self.extra_environ)
        model.Session.remove()

    def test_10_edit(self):
        # Test Packages Entity Put 200.

        # create a package with testvalues
        if not model.Package.by_name(self.testvalues['name']):
            pkg = model.Package()
            pkg.name = self.testvalues['name']
            rev = model.repo.new_revision()
            model.Session.commit()

            pkg = model.Package.by_name(self.testvalues['name'])
            model.setup_default_user_roles(pkg, [self.user])
            rev = model.repo.new_revision()
            model.repo.commit_and_remove()
        assert model.Package.by_name(self.testvalues['name'])

        # edit it
        pkg_vals = {'name':u'somethingnew', 'title':u'newtesttitle'}
        offset = '/api/rest/package/%s' % self.testvalues['name']
        postparams = '%s=1' % simplejson.dumps(pkg_vals)
        res = self.app.post(offset, params=postparams, status=[200],
                            extra_environ=self.extra_environ)
        model.Session.remove()
        pkg = model.Package.query.filter_by(name=pkg_vals['name']).one()
        assert pkg.title == pkg_vals['title']

    def test_10_edit_name_duplicate(self):
        # create a package with testvalues
        if not model.Package.by_name(self.testvalues['name']):
            pkg = model.Package()
            pkg.name = self.testvalues['name']
            rev = model.repo.new_revision()
            model.Session.commit()

            pkg = model.Package.by_name(self.testvalues['name'])
            model.setup_default_user_roles(pkg, [self.user])
            rev = model.repo.new_revision()
            model.repo.commit_and_remove()
        assert model.Package.by_name(self.testvalues['name'])
        
        # create a package with name 'dupname'
        dupname = u'dupname'
        if not model.Package.by_name(dupname):
            pkg = model.Package()
            pkg.name = dupname
            rev = model.repo.new_revision()
            model.Session.commit()
        assert model.Package.by_name(dupname)

        # edit first package to have dupname
        pkg_vals = {'name':dupname}
        offset = '/api/rest/package/%s' % self.testvalues['name']
        postparams = '%s=1' % simplejson.dumps(pkg_vals)
        res = self.app.post(offset, params=postparams, status=[409],
                            extra_environ=self.extra_environ)
        model.Session.remove()
        
    def test_11_delete(self):
        # Test Packages Entity Delete 200.

        # create a package with testvalues
        if not model.Package.by_name(self.testvalues['name']):
            pkg = model.Package()
            pkg.name = self.testvalues['name']
            rev = model.repo.new_revision()
            model.repo.commit_and_remove()

            pkg = model.Package.by_name(self.testvalues['name'])
            model.setup_default_user_roles(pkg, [self.user])
            rev = model.repo.new_revision()
            model.repo.commit_and_remove()
        assert model.Package.by_name(self.testvalues['name'])

        # delete it
        offset = '/api/rest/package/%s' % self.testvalues['name']
        rev = model.repo.new_revision()
        res = self.app.delete(offset, status=[200],
                extra_environ=self.extra_environ)
        pkg = model.Package.by_name(self.testvalues['name'])
        assert pkg.state.name == 'deleted'
        model.Session.remove()

    def test_12_get_404(self):
        # Test Package Entity Get 404.
        assert not model.Package.query.filter_by(name=self.testvalues['name']).count()
        offset = '/api/rest/package/%s' % self.testvalues['name']
        res = self.app.get(offset, status=404)
        model.Session.remove()

    def test_13_delete_404(self):
        # Test Packages Entity Delete 404.
        assert not model.Package.query.filter_by(name=self.testvalues['name']).count()
        offset = '/api/rest/package/%s' % self.testvalues['name']
        res = self.app.delete(offset, status=[404],
                              extra_environ=self.extra_environ)

class TestSearch(TestController):
    @classmethod
    def setup_class(self):
        try:
            CreateTestData.delete()
        except:
            pass
        model.Session.remove()
        CreateTestData.create()
        self.base_url = '/api/search/package'

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        CreateTestData.delete()

    def setup(self):
        self.testvalues = {
            'name' : u'testpkg',
            'title': 'Some Title',
            'url': u'http://blahblahblah.mydomain',
            'download_url': u'http://blahblahblah.mydomain',
            'tags': 'russion novel',
            'license_id': '4',
        }

        self.pkg = model.Package()
        self.pkg.name = self.testvalues['name']
        rev = model.repo.new_revision()

        model.Session.commit()
        model.Session.remove()


    def teardown(self):
        model.Session.remove()
        pkg = model.Package.by_name(self.testvalues['name'])
        if pkg:
            pkg.purge()
        model.Session.commit()
        model.Session.remove()

    def test_1_uri_q(self):
        offset = self.base_url + '?q=%s' % self.testvalues['name']
        res = self.app.get(offset, status=200)
        res_dict = simplejson.loads(res.body)
        assert u'testpkg' in res_dict['results'], res_dict['results']
        assert res_dict['count'] == 1, res_dict['count']

    def test_2_post_q(self):
        offset = self.base_url
        query = {'q':'testpkg'}
        res = self.app.post(offset, params=query, status=200)
        res_dict = simplejson.loads(res.body)
        assert u'testpkg' in res_dict['results'], res_dict['results']
        assert res_dict['count'] == 1, res_dict['count']

    def test_3_uri_qjson(self):
        query = {'q': self.testvalues['name']}
        json_query = simplejson.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = simplejson.loads(res.body)
        assert u'testpkg' in res_dict['results'], res_dict['results']
        assert res_dict['count'] == 1, res_dict['count']

    def test_4_post_qjson(self):
        query = {'q': self.testvalues['name']}
        json_query = simplejson.dumps(query)
        offset = self.base_url
        res = self.app.post(offset, params=json_query, status=200)
        res_dict = simplejson.loads(res.body)
        assert u'testpkg' in res_dict['results'], res_dict['results']
        assert res_dict['count'] == 1, res_dict['count']

    def test_5_uri_qjson_tags(self):
        query = {'q': 'annakarenina tags:russian tags:tolstoy'}
        json_query = simplejson.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = simplejson.loads(res.body)
        assert u'annakarenina' in res_dict['results'], res_dict['results']
        assert res_dict['count'] == 1, res_dict
        
    def test_5_uri_qjson_tags_multiple(self):
        query = {'q': 'tags:russian tags:tolstoy'}
        json_query = simplejson.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = simplejson.loads(res.body)
        assert u'annakarenina' in res_dict['results'], res_dict['results']
        assert res_dict['count'] == 1, res_dict

    def test_6_uri_q_tags(self):
        query = webhelpers.util.html_escape('annakarenina tags:russian tags:tolstoy')
        offset = self.base_url + '?q=%s' % query
        res = self.app.get(offset, status=200)
        res_dict = simplejson.loads(res.body)
        assert u'annakarenina' in res_dict['results'], res_dict['results']
        assert res_dict['count'] == 1, res_dict['count']

    def test_7_uri_qjson_tags(self):
        query = {'q': '', 'tags':['tolstoy']}
        json_query = simplejson.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = simplejson.loads(res.body)
        assert u'annakarenina' in res_dict['results'], res_dict['results']
        assert res_dict['count'] == 1, res_dict

    def test_7_uri_qjson_tags_multiple(self):
        query = {'q': '', 'tags':['tolstoy', 'russian']}
        json_query = simplejson.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = simplejson.loads(res.body)
        assert u'annakarenina' in res_dict['results'], res_dict['results']
        assert res_dict['count'] == 1, res_dict

    def test_7_uri_qjson_tags_reverse(self):
        query = {'q': '', 'tags':['russian']}
        json_query = simplejson.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = simplejson.loads(res.body)
        assert u'annakarenina' in res_dict['results'], res_dict['results']
        assert res_dict['count'] == 2, res_dict

    def test_8_all_fields(self):
        query = {'q': 'russian', 'all_fields':1}
        json_query = simplejson.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = simplejson.loads(res.body)
        assert res_dict['count'] == 2, res_dict
        print res_dict['results']
        assert res_dict['results'][0]['name'] == 'annakarenina', res_dict['results']
        assert res_dict['results'][0]['title'] == 'A Novel By Tolstoy', res_dict['results']
        assert res_dict['results'][0]['license'] == 'OKD Compliant::Other', res_dict['results'][0]['license']
        assert res_dict['results'][0]['tags'] == ['russian', 'tolstoy'], res_dict['results'][0]['tags']

    def test_9_just_tags(self):
        offset = self.base_url + '?tags=russian&all_fields=1'
        res = self.app.get(offset, status=200)
        res_dict = simplejson.loads(res.body)
        assert res_dict['count'] == 2, res_dict

    def test10_multiple_tags_with_plus(self):
        offset = self.base_url + '?tags=tolstoy+russian&all_fields=1'
        res = self.app.get(offset, status=200)
        res_dict = simplejson.loads(res.body)
        assert res_dict['count'] == 1, res_dict

    def test10_multiple_tags_with_ampersand(self):
        offset = self.base_url + '?tags=tolstoy&tags=russian&all_fields=1'
        res = self.app.get(offset, status=200)
        res_dict = simplejson.loads(res.body)
        assert res_dict['count'] == 1, res_dict

    def test10_many_tags_with_ampersand(self):
        offset = self.base_url + '?tags=tolstoy&tags=russian&tags=tolstoy'
        res = self.app.get(offset, status=200)
        res_dict = simplejson.loads(res.body)
        assert res_dict['count'] == 1, res_dict

    def test11_pagination_limit(self):
        offset = self.base_url + '?all_fields=1&tags=russian&limit=1'
        res = self.app.get(offset, status=200)
        res_dict = simplejson.loads(res.body)
        assert res_dict['count'] == 2, res_dict
        assert len(res_dict['results']) == 1, res_dict
        assert res_dict['results'][0]['name'] == 'annakarenina', res_dict['results'][0]['name']

    def test11_pagination_offset_limit(self):
        offset = self.base_url + '?all_fields=1&tags=russian&offset=1&limit=1'
        res = self.app.get(offset, status=200)
        res_dict = simplejson.loads(res.body)
        assert res_dict['count'] == 2, res_dict
        assert len(res_dict['results']) == 1, res_dict
        assert res_dict['results'][0]['name'] == 'warandpeace', res_dict['results'][0]['name']

