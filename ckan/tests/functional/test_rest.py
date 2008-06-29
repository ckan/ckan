from ckan.tests import *
import ckan.models
import simplejson

class TestRestController(TestController2):

    def setup_method(self, name):
        self.testvalues = {
            'name' : 'testpkg',
            #'url': 'http://blahblahblah.mydomain',
            #'download_url': 'http://blahblahblah.mydomain',
        }

    def teardown_method(self, name):
        rev = ckan.models.repo.youngest_revision()
        try:
            rev.model.packages.purge(self.testvalues['name'])
        except:
            pass

    def test_rest_package(self):
        # Test Packages Register Get 401.
        # Test Packages Register Post 401.
        # Test Packages Entity Get 401.
        # Test Packages Entity Put 401.
        # Test Packages Entity Delete 401.
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
        postparams = '%s=1' % simplejson.dumps(self.testvalues)
        res = self.app.post(offset, params=postparams, status=[200])

        # Test Package Entity Get 200.
        offset = '/api/rest/package/%s' % self.testvalues['name']
        res = self.app.get(offset, status=[200])
        
        # Test Packages Register Post 409.
        offset = '/api/rest/package'
        postparams = '%s=1' % simplejson.dumps(self.testvalues)
        res = self.app.post(offset, params=postparams, status=[409])

        # Test Package Entity Put 404.
        offset = '/api/rest/package/22222'
        postparams = '%s=1' % simplejson.dumps(self.testvalues)
        res = self.app.post(offset, params=postparams, status=[404])

        # Test Packages Entity Put 200.
        offset = '/api/rest/package/%s' % self.testvalues['name']
        postparams = '%s=1' % simplejson.dumps(self.testvalues)
        res = self.app.post(offset, params=postparams, status=[200])
        
        # Test Packages Entity Delete 200.

