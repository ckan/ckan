from ckan.tests import *
import ckan.model as model
import simplejson

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
            # Todo: Add tags and licenses.
            'name' : u'testpkg',
            'url': u'http://blahblahblah.mydomain',
            'download_url': u'http://blahblahblah.mydomain',
        }
        self.random_name = u'http://myrandom.openidservice.org/'
        self.apikey = model.ApiKey(name=self.random_name)
        model.Session.commit()
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

    def test_rest_package(self):
        # Test Packages Register Post 401.
        offset = '/api/rest/package'
        postparams = '%s=1' % simplejson.dumps(self.testvalues)
        res = self.app.post(offset, params=postparams, status=[401,403])
        model.Session.remove()

        # Test Packages Entity Put 401.
        offset = '/api/rest/package/%s' % self.testvalues['name']
        postparams = '%s=1' % simplejson.dumps(self.testvalues)
        res = self.app.post(offset, params=postparams, status=[401,403])
        model.Session.remove()

        # Test Packages Entity Delete 401.
        offset = '/api/rest/package/%s' % self.testvalues['name']
        res = self.app.delete(offset, status=[401,403])
        # Todo: Figure out authentication for REST API.
        model.Session.remove()

        # Test Packages Register Get 200.
        offset = '/api/rest/package/annakarenina'
        res = self.app.get(offset, status=[200])
        assert 'annakarenina' in res
        model.Session.remove()

        # Test Package Entity Get 404.
        offset = '/api/rest/package/22222'
        res = self.app.get(offset, status=404)
        model.Session.remove()

        # Test Packages Register Post 200.
        offset = '/api/rest/package'
        extra_environ={ 'Authorization' : str(self.apikey.key) }
        postparams = '%s=1' % simplejson.dumps(self.testvalues)
        res = self.app.post(offset, params=postparams, status=[200],
                extra_environ=extra_environ)
        model.Session.remove()

        # Test Package Entity Get 200.
        offset = '/api/rest/package/%s' % self.testvalues['name']
        res = self.app.get(offset, status=[200])
        model.Session.remove()
        
        # Test Packages Register Post 409.
        offset = '/api/rest/package'
        postparams = '%s=1' % simplejson.dumps(self.testvalues)
        res = self.app.post(offset, params=postparams, status=[409],
                extra_environ=extra_environ)
        model.Session.remove()

        # TODO: get this working again. At present returns 400
        # Test Package Entity Put 404.
        offset = '/api/rest/package/22222'
        postparams = '%s=1' % simplejson.dumps(self.testvalues)
        # res = self.app.post(offset, params=postparams, status=[404],
        #        extra_environ=extra_environ)
        model.Session.remove()

        # Test Packages Entity Put 200.
        # Todo: Change title, url, tags, licenses. Check values get changed.
        offset = '/api/rest/package/%s' % self.testvalues['name']
        postparams = '%s=1' % simplejson.dumps(self.testvalues)
        res = self.app.post(offset, params=postparams, status=[200],
                extra_environ=extra_environ)
        model.Session.remove()
        
        # Test Packages Entity Delete 200.
        offset = '/api/rest/package/%s' % self.testvalues['name']
        res = self.app.delete(offset, status=[200],
                extra_environ=extra_environ)
        model.Session.remove()

        # Test Package Entity Get 404.
        offset = '/api/rest/package/%s' % self.testvalues['name']
        res = self.app.get(offset, status=404)
        model.Session.remove()

        # Test Packages Entity Delete 404.
        offset = '/api/rest/package/%s' % self.testvalues['name']
        res = self.app.delete(offset, status=[404],
                extra_environ=extra_environ)

