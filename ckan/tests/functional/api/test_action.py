from ckan.lib.create_test_data import CreateTestData
import ckan.model as model
from ckan.tests import WsgiAppCase
import json
from pprint import pprint, pformat

class TestAction(WsgiAppCase):

    @classmethod
    def setup_class(self):
        CreateTestData.create()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_01_package_list(self):
        postparams = '%s=1' % json.dumps({})
        res = self.app.post('/api/action/package_list', params=postparams)
        assert json.loads(res.body) == {"help": "Lists the package by name",
                                        "success": True,
                                        "result": ["annakarenina", "warandpeace"]}

    def test_02_package_autocomplete(self):
        query = 'a'
        res = self.app.get('/package/autocomplete?q=%s' % query)
        assert res.body == "annakarenina|annakarenina\nA Wonderful Story (warandpeace)|warandpeace"

    def test_03_create_update_package(self):

        package = {
            'author': None,
            'author_email': None,
            'extras': [{'key': u'original media','value': u'"book"'}],
            'license_id': u'other-open',
            'maintainer': None,
            'maintainer_email': None,
            'name': u'annakareninanew',
            'notes': u'Some test now',
            'resources': [{'alt_url': u'alt123',
                           'description': u'Full text.',
                           'extras': {u'alt_url': u'alt123', u'size': u'123'},
                           'format': u'plain text',
                           'hash': u'abc123',
                           'position': 0,
                           'url': u'http://www.annakarenina.com/download/'},
                          {'alt_url': u'alt345',
                           'description': u'Index of the novel',
                           'extras': {u'alt_url': u'alt345', u'size': u'345'},
                           'format': u'json',
                           'hash': u'def456',
                           'position': 1,
                           'url': u'http://www.annakarenina.com/index.json'}],
            'tags': [{'name': u'russian'}, {'name': u'tolstoy'}],
            'title': u'A Novel By Tolstoy',
            'url': u'http://www.annakarenina.com',
            'version': u'0.7a'
        }

        wee = json.dumps(package)
        postparams = '%s=1' % json.dumps(package)
        res = self.app.post('/api/action/package_create', params=postparams,
                            extra_environ={'Authorization': 'tester'})
        package_created = json.loads(res.body)['result']
        print package_created
        package_created['name'] = 'moo'
        postparams = '%s=1' % json.dumps(package_created)
        res = self.app.post('/api/action/package_update', params=postparams,
                            extra_environ={'Authorization': 'tester'})

        package_updated = json.loads(res.body)['result']
        package_updated.pop('revision_id')
        package_updated.pop('revision_timestamp')
        package_created.pop('revision_id')
        package_created.pop('revision_timestamp')
        assert package_updated == package_created#, (pformat(json.loads(res.body)), pformat(package_created['result']))


