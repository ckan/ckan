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
        postparams = '%s=1' % json.dumps({'q':'a'})
        res = self.app.post('/api/action/package_autocomplete', params=postparams)
        res_obj = json.loads(res.body)
        assert res_obj['success'] == True
        assert res_obj['result'][0]['name'] == 'annakarenina'

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

    def test_04_user_list(self):
        postparams = '%s=1' % json.dumps({})
        res = self.app.post('/api/action/user_list', params=postparams)
        res_obj = json.loads(res.body)
        assert res_obj['help'] == 'Lists the current users'
        assert res_obj['success'] == True
        assert len(res_obj['result']) == 7
        assert res_obj['result'][0]['name'] == 'annafan'
        assert res_obj['result'][0]['about'] == 'I love reading Annakarenina. My site: <a href="http://anna.com">anna.com</a>'
        assert not 'apikey' in res_obj['result'][0]

    def test_05_user_show(self):
        postparams = '%s=1' % json.dumps({'id':'annafan'})
        res = self.app.post('/api/action/user_show', params=postparams)
        res_obj = json.loads(res.body)
        assert res_obj['help'] == 'Shows user details'
        assert res_obj['success'] == True
        result = res_obj['result']
        assert result['name'] == 'annafan'
        assert result['about'] == 'I love reading Annakarenina. My site: <a href="http://anna.com">anna.com</a>'
        assert 'apikey' in result
        assert 'activity' in result
        assert 'created' in result
        assert 'display_name' in result
        assert 'number_administered_packages' in result
        assert 'number_of_edits' in result

    def test_06_tag_list(self):
        postparams = '%s=1' % json.dumps({})
        res = self.app.post('/api/action/tag_list', params=postparams)
        assert json.loads(res.body) == {'help': 'Lists tags by name',
                                        'success': True,
                                        'result': ['russian', 'tolstoy']}

    def test_07_tag_show(self):
        postparams = '%s=1' % json.dumps({'id':'russian'})
        res = self.app.post('/api/action/tag_show', params=postparams)
        res_obj = json.loads(res.body)
        assert res_obj['help'] == 'Shows tag details'
        assert res_obj['success'] == True
        result = res_obj['result']
        assert result['name'] == 'russian'
        assert 'id' in result
        assert 'packages' in result and len(result['packages']) == 3 
        assert [package['name'] for package in result['packages']].sort() == ['annakarenina', 'warandpeace', 'moo'].sort()
