from ckan.tests import *
import ckan.models as model
import simplejson

class TestRestController(TestController2):

    def setup_method(self, name):
        self.testvalues = {
            # Todo: Add tags and licenses.
            'name' : 'testpkg',
            'url': 'http://blahblahblah.mydomain',
            'download_url': 'http://blahblahblah.mydomain',
        }
        self.random_name = 'http://myrandom.openidservice.org/'
        self.apikey = model.ApiKey(name=self.random_name)

    def teardown_method(self, name):
        apikey = model.ApiKey.byName(self.random_name)
        model.ApiKey.delete(apikey.id)
        rev = model.repo.youngest_revision()
        try:
            rev.model.packages.purge(self.testvalues['name'])
        except:
            pass

    def test_rest_package(self):
        # Test Packages Register Post 401.
        offset = '/api/rest/package'
        postparams = '%s=1' % simplejson.dumps(self.testvalues)
        res = self.app.post(offset, params=postparams, status=[401])

        # Test Packages Entity Put 401.
        offset = '/api/rest/package/%s' % self.testvalues['name']
        postparams = '%s=1' % simplejson.dumps(self.testvalues)
        res = self.app.post(offset, params=postparams, status=[401])

        # Test Packages Entity Delete 401.
        offset = '/api/rest/package/%s' % self.testvalues['name']
        res = self.app.delete(offset, status=[401])
        # Todo: Figure out authentication for REST API.

        # Test Packages Register Get 200.
        offset = '/api/rest/package/annakarenina'
        res = self.app.get(offset, status=[200])
        assert 'annakarenina' in res

        # Test Package Entity Get 404.
        offset = '/api/rest/package/22222'
        res = self.app.get(offset, status=404)

        # Test Packages Register Post 200.
        offset = '/api/rest/package'
        extra_environ={ 'Authorization' : str(self.apikey.key) }
        postparams = '%s=1' % simplejson.dumps(self.testvalues)
        res = self.app.post(offset, params=postparams, status=[200],
                extra_environ=extra_environ)

        # Test Package Entity Get 200.
        offset = '/api/rest/package/%s' % self.testvalues['name']
        res = self.app.get(offset, status=[200])
        
        # Test Packages Register Post 409.
        offset = '/api/rest/package'
        postparams = '%s=1' % simplejson.dumps(self.testvalues)
        res = self.app.post(offset, params=postparams, status=[409],
                extra_environ=extra_environ)

        # Test Package Entity Put 404.
        offset = '/api/rest/package/22222'
        postparams = '%s=1' % simplejson.dumps(self.testvalues)
        res = self.app.post(offset, params=postparams, status=[404],
                extra_environ=extra_environ)

        # Test Packages Entity Put 200.
        # Todo: Change title, url, tags, licenses. Check values get changed.
        offset = '/api/rest/package/%s' % self.testvalues['name']
        postparams = '%s=1' % simplejson.dumps(self.testvalues)
        res = self.app.post(offset, params=postparams, status=[200],
                extra_environ=extra_environ)
        
        # Test Packages Entity Delete 200.
        offset = '/api/rest/package/%s' % self.testvalues['name']
        res = self.app.delete(offset, status=[200],
                extra_environ=extra_environ)

        # Test Package Entity Get 404.
        offset = '/api/rest/package/%s' % self.testvalues['name']
        res = self.app.get(offset, status=404)

        # Test Packages Entity Delete 404.
        offset = '/api/rest/package/%s' % self.testvalues['name']
        res = self.app.delete(offset, status=[404],
                extra_environ=extra_environ)

