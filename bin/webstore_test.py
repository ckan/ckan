'''This is a test using the real setup with elasticsearch.

It requires you to run nginx on port 8088 with config as per
https://github.com/okfn/elastic-proxy/blob/master/elasticproxy plus,
obviously, elasticsearch on port 9200.
'''
import json
import paste.fixture
import paste.proxy
import urllib2

ckan_url = 'http://localhost:8088'
app = paste.proxy.Proxy(ckan_url)
testapp = paste.fixture.TestApp(app)

class TestWebstoreExternal:
    def test_01(self):
        out = testapp.get('/api/rest/dataset/annakarenina')
        dataset = json.loads(out.body)
        resource_id = dataset['resources'][0]['id']

        offset = '/api/data/%s' % resource_id
        res = testapp.get(offset, status=400)
        assert res.status == 400

        offset = '/api/data/%s/_search?q=a' % resource_id
        res = testapp.get(offset)
        assert res.status == 200
        out = json.loads(res.body)
        assert out['hits']['total'] == 0

        data = {
            "user": "hamlet",
            "post_date": "2009-11-15T13:12:00",
            "message": "Trying out elasticsearch, so far so good?"
            }
        data = json.dumps(data)
        offset = '/api/data/%s' % resource_id
        testapp.put(offset + '/1', data)
        out = testapp.get(offset + '/1')
        outdata = json.loads(out.body)
        assert outdata['_source']['user'] == 'hamlet', outdata

        offset = '/api/data/%s/_search?q=hamlet' % resource_id
        res = testapp.get(offset)
        assert res.status == 200
        out = json.loads(res.body)
        assert out['hits']['total'] == 1, out

        # TODO: test delete ...
#        offset = '/api/data/%s' % resource_id
#        testapp.delete(offset + '/1')
#
#        offset = '/api/data/%s/_search?q=hamlet' % resource_id
#        res = testapp.get(offset)
#        assert res.status == 200
#        out = json.loads(res.body)
#        assert out['hits']['total'] == 0, out

