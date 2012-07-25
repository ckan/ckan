import socket
import json
import time
import requests

from nose.plugins.skip import SkipTest
from pylons import config

from ckan.tests import TestController, CreateTestData
import ckan.model as model
from ckan.lib.helpers import url_for


ELASTIC_SEARCH_HOST = config.get('elastic_search_host', '0.0.0.0:9200')


class MockResponse(object):
    '''Mock Requests response

    A mock object to make paster responses look like the ones returned
    by Requests (only the useful properties are used)

    '''

    def __init__(self, res):
        '''
            :param res: a response object returned by the paster test app
        '''
        self.status_code = res.status
        self.content = res.body
        self.headers = res.header_dict


class MockProxyServer(object):
    '''Mock proxy server to Elastic Search

    A mock class used to mimic Nginx forwarding to Elastic Search when
    querying the CKAN data API. It basically does two requests, one to
    the CKAN controller, and a second one to Elastic Search, using the
    value of the 'X-Accel-Redirect' header.

    '''

    def __init__(self, app):
        '''
            :param app: a paster test application
        '''

        self.elastic_search_host = ELASTIC_SEARCH_HOST

        self.app = app

    def _get_elastic_search_offset(self, res):
        '''
            :param res: a response object returned by the paster test app
        '''

        redirect = dict(res.headers).get('X-Accel-Redirect')

        # Remove the /elastic bit
        return redirect[8:] if redirect else None

    def _forward_request(self, res, data=None):
        '''
            :param res: a response object returned by the paster test app
            :param data: a dictionary of data to be sent to ES. Will produce
                a POST request
        '''

        elastic_search_offset = self._get_elastic_search_offset(res)

        if res.status != 200 and not elastic_search_offset:
            # No need to forward, return a Requests-like response
            return MockResponse(res)

        assert elastic_search_offset

        if data:
            res = requests.post('http://%s%s' % (self.elastic_search_host, elastic_search_offset), data=json.dumps(data))
        else:
            res = requests.get('http://%s%s' % (self.elastic_search_host, elastic_search_offset))

        return res

    def get(self, offset, ckan_status=200, extra_environ=None):
        '''
            :param offset: CKAN route to request
            :param ckan_status: expected status to be returned, will throw an
                exception if different from the actually returned
        '''

        res = self.app.get(offset, status=ckan_status, extra_environ=extra_environ)
        return self._forward_request(res)

    def post(self, offset, data=None, ckan_status=200, extra_environ=None):
        '''
            :param offset: CKAN route to request
            :param data: a dictionary of data to be sent to ES.
            :param ckan_status: expected status to be returned, will throw an
                exception if different from the actually returned
        '''

        res = self.app.post(offset, params=data, status=ckan_status, extra_environ=extra_environ)
        return self._forward_request(res, data)


class TestDatastoreController(TestController):

    @classmethod
    def setup_class(cls):

        # Check if Elastic Search is available, otherwise skip tests
        try:
            res = requests.get('http://%s/_status' % ELASTIC_SEARCH_HOST, timeout=2)
            if res.status_code == 200:
                try:
                    content = json.loads(res.content)
                    if not 'ok'in content or not '_shards' in content:
                        raise ValueError
                except ValueError:
                    raise SkipTest('This does not look like Elastic Search, skipping...')
            else:
                raise SkipTest('Could not reach Elastic Search, skipping...')

        except (requests.exceptions.RequestException, socket.timeout), e:
            raise SkipTest('Could not reach Elastic Search, skipping... (%r)' % e)

        # Push dummy data to create the test index
        requests.put('http://%s/ckan-%s/' % (ELASTIC_SEARCH_HOST, config.get('ckan.site_id')))

        model.repo.init_db()
        CreateTestData.create()

    @classmethod
    def teardown_class(self):

        # Delete the test index on ES
        requests.delete('http://%s/ckan-%s/' % (ELASTIC_SEARCH_HOST, config.get('ckan.site_id')))

        model.repo.rebuild_db()

    # TODO: do we test authz. In essence authz is same as for resource read /
    # edit which in turn is same as dataset read / edit and which is tested
    # extensively elsewhere ...
    def test_basic(self):

        mock_server = MockProxyServer(self.app)

        # Create a dataset, the resource should have the webstore_url
        # extra empty
        dataset = model.Package.by_name(CreateTestData.pkg_names[0])
        resource_id = dataset.resources[0].id

        assert not dataset.resources[0].webstore_url

        offset_wrong_read = url_for('datastore_read', id='wrong_resource_id')
        offset_wrong_write = url_for('datastore_write', id='wrong_resource_id')
        offset_read = url_for('datastore_read', id=resource_id)
        offset_write = url_for('datastore_write', id=resource_id)

        # Resource not found
        res = mock_server.get(offset_wrong_read, ckan_status=404)
        assert 'Resource not found' in res.content
        res = mock_server.post(offset_wrong_write, ckan_status=404, data={'a': 1})
        assert 'Resource not found' in res.content

        # Empty datastore
        res = mock_server.get(offset_read)

        assert res.status_code == 400
        assert 'No handler found for uri' in res.content
        assert resource_id in res.content

        res = mock_server.get(offset_read + '/_mapping')
        content = json.loads(res.content)

        assert res.status_code == 404
        assert content['status'] == 404
        assert 'TypeMissingException' in content['error']
        assert resource_id in content['error']

        # Push some stuff via the data API
        data = {'a': 1, 'b': 2.78, 'c': 'test'}

        # Non logged users can not push the datastore
        res = mock_server.post(offset_write + '/1', data, ckan_status=302)

        extra_environ = {'REMOTE_USER':'annafan'}
        res = mock_server.post(offset_write + '/1', data, extra_environ=extra_environ)

        content = json.loads(res.content)
        assert content['ok'] == True
        assert content['_index'] == 'ckan-%s' % config.get('ckan.site_id')

        # We need to wait or ES returns 0 hits
        time.sleep(1)

        # Query the data API
        res = mock_server.get(offset_read + '/_mapping')
        content = json.loads(res.content)

        assert content == {resource_id: {
                                'properties': {
                                    'a': {'type': 'long'},
                                    'b': {'type': 'double'},
                                    'c': {'type': 'string'}
                                    }
                                }
                             }

        res = mock_server.get(offset_read + '/_search')
        content = json.loads(res.content)
        assert content['hits']['total'] == 1
        assert content['hits']['hits'][0]['_source'] == data

        # Check that the webstore_url extra was set to active
        dataset = model.Package.by_name(CreateTestData.pkg_names[0])
        assert dataset.resources[0].webstore_url == u'active'
