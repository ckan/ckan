from ckan.tests import *
import ckan.model as model
import simplejson

ACCESS_DENIED = [401,403]

class TestRestController(TestController2):

    @classmethod
    def setup_class(self):
        try:
            CreateTestData.delete()
        except:
            pass
        model.Session.remove()
        CreateTestData.create()

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
        self.random_name = u'http://myrandom.openidservice.org/'
        self.apikey = model.ApiKey(name=self.random_name)
        model.Session.commit()
        self.extra_environ={ 'Authorization' : str(self.apikey.key) }
        model.Session.remove()


    def teardown(self):
        model.Session.remove()
        apikey = model.ApiKey.by_name(self.random_name)
        if apikey:
            apikey.purge()
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
        offset = '/api/rest/package/%s' % self.testvalues['name']
        postparams = '%s=1' % simplejson.dumps(self.testvalues)
        res = self.app.post(offset, params=postparams, status=ACCESS_DENIED)

    def test_01_entity_delete_noauth(self):
        # Test Packages Entity Delete 401.
        offset = '/api/rest/package/%s' % self.testvalues['name']
        res = self.app.delete(offset, status=ACCESS_DENIED)
        # Todo: Figure out authentication for REST API.

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
        assert model.Package.by_name(self.testvalues['name'])

        # edit it
        pkg_vals = {'name':'somethingnew', 'title':'newtesttitle'}
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
        assert model.Package.by_name(self.testvalues['name'])
        
        # create a package with name 'dupname'
        dupname = 'dupname'
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
            model.Session.commit()
        assert model.Package.by_name(self.testvalues['name'])

        # delete it
        offset = '/api/rest/package/%s' % self.testvalues['name']
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

    def _test_14_search_name(self):
        # TODO: REST Search?
        # create a package with testvalues
        if not model.Package.by_name(self.testvalues['name']):
            pkg = model.Package()
            pkg.name = self.testvalues['name']
            rev = model.repo.new_revision()
            model.Session.commit()
        pkg = model.Package.by_name(self.testvalues['name'])
        assert pkg

        # do search
        offset = '/api/rest/search/%s' % self.testvalues['name']
        res = self.app.get(offset, status=200)
        assert '"name": "testpkg"' in res, res

        
