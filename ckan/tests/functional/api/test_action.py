import re
import json
from pprint import pprint, pformat
from nose.tools import assert_equal

from ckan.lib.create_test_data import CreateTestData
import ckan.model as model
from ckan.tests import WsgiAppCase
from ckan.tests.functional.api import assert_dicts_equal_ignoring_ordering, change_lists_to_sets

class TestAction(WsgiAppCase):

    STATUS_200_OK = 200
    STATUS_201_CREATED = 201
    STATUS_400_BAD_REQUEST = 400
    STATUS_403_ACCESS_DENIED = 403
    STATUS_404_NOT_FOUND = 404
    STATUS_409_CONFLICT = 409

    sysadmin_user = None
    
    normal_user = None

    @classmethod
    def setup_class(self):
        CreateTestData.create()
        self.sysadmin_user = model.User.get('testsysadmin')
        self.normal_user = model.User.get('annafan')

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_01_package_list(self):
        postparams = '%s=1' % json.dumps({})
        res = self.app.post('/api/action/package_list', params=postparams)
        assert_dicts_equal_ignoring_ordering(
            json.loads(res.body),
            {"help": "Lists packages by name or id",
             "success": True,
             "result": ["annakarenina", "warandpeace"]})

    def test_01_package_show(self):
        anna_id = model.Package.by_name(u'annakarenina').id
        postparams = '%s=1' % json.dumps({'id': anna_id})
        res = self.app.post('/api/action/package_show', params=postparams)
        res_dict = json.loads(res.body)
        assert_equal(res_dict['success'], True)
        assert_equal(res_dict['help'], None)
        pkg = res_dict['result']
        assert_equal(pkg['name'], 'annakarenina')
        missing_keys = set(('title', 'groups')) - set(pkg.keys())
        assert not missing_keys, missing_keys

    def test_01_package_show_with_jsonp(self):
        anna_id = model.Package.by_name(u'annakarenina').id
        postparams = '%s=1' % json.dumps({'id': anna_id})
        res = self.app.post('/api/action/package_show?callback=jsoncallback', params=postparams)

        assert re.match('jsoncallback\(.*\);', res.body), res
        # Unwrap JSONP callback (we want to look at the data).
        msg = res.body[len('jsoncallback')+1:-2]
        res_dict = json.loads(msg)
        assert_equal(res_dict['success'], True)
        assert_equal(res_dict['help'], None)
        pkg = res_dict['result']
        assert_equal(pkg['name'], 'annakarenina')
        missing_keys = set(('title', 'groups')) - set(pkg.keys())
        assert not missing_keys, missing_keys
                
    def test_02_package_autocomplete(self):
        postparams = '%s=1' % json.dumps({'q':'war'})
        res = self.app.post('/api/action/package_autocomplete', params=postparams)
        res_obj = json.loads(res.body)
        assert res_obj['success'] == True
        pprint(res_obj['result'][0]['name'])
        assert res_obj['result'][0]['name'] == 'warandpeace'

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

    def test_18_create_package_not_authorized(self):

        package = {
            'extras': [{'key': u'original media','value': u'"book"'}],
            'license_id': u'other-open',
            'maintainer': None,
            'maintainer_email': None,
            'name': u'annakareninanew_not_authorized',
            'notes': u'Some test now',
            'tags': [{'name': u'russian'}, {'name': u'tolstoy'}],
            'title': u'A Novel By Tolstoy',
            'url': u'http://www.annakarenina.com',
        }

        wee = json.dumps(package)
        postparams = '%s=1' % json.dumps(package)
        res = self.app.post('/api/action/package_create', params=postparams,
                                     status=self.STATUS_403_ACCESS_DENIED)

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
        # Anonymous request
        postparams = '%s=1' % json.dumps({'id':'annafan'})
        res = self.app.post('/api/action/user_show', params=postparams)
        res_obj = json.loads(res.body)
        assert res_obj['help'] == 'Shows user details'
        assert res_obj['success'] == True
        result = res_obj['result']
        assert result['name'] == 'annafan'
        assert result['about'] == 'I love reading Annakarenina. My site: <a href="http://anna.com">anna.com</a>'
        assert 'activity' in result
        assert 'created' in result
        assert 'display_name' in result
        assert 'number_administered_packages' in result
        assert 'number_of_edits' in result
        assert not 'apikey' in result
        assert not 'reset_key' in result

        # Same user can see his api key
        res = self.app.post('/api/action/user_show', params=postparams,
                            extra_environ={'Authorization': str(self.normal_user.apikey)})

        res_obj = json.loads(res.body)
        result = res_obj['result']
        assert result['name'] == 'annafan'
        assert 'apikey' in result
        assert 'reset_key' in result

        # Sysadmin user can see everyone's api key
        res = self.app.post('/api/action/user_show', params=postparams,
                            extra_environ={'Authorization': str(self.sysadmin_user.apikey)})

        res_obj = json.loads(res.body)
        result = res_obj['result']
        assert result['name'] == 'annafan'
        assert 'apikey' in result
        assert 'reset_key' in result

    def test_05_user_show_edits(self):
        postparams = '%s=1' % json.dumps({'id':'tester'})
        res = self.app.post('/api/action/user_show', params=postparams)
        res_obj = json.loads(res.body)
        assert res_obj['help'] == 'Shows user details'
        assert res_obj['success'] == True
        result = res_obj['result']
        assert result['name'] == 'tester'
        assert_equal(result['about'], None)
        assert result['number_of_edits'] >= 1
        edit = result['activity'][-1] # first edit chronologically
        assert_equal(edit['author'], 'tester')
        assert 'timestamp' in edit
        assert_equal(edit['state'], 'active')
        assert_equal(edit['approved_timestamp'], None)
        assert_equal(set(edit['groups']), set(('roger', 'david')))
        assert_equal(edit['state'], 'active')
        assert edit['message'].startswith('Creating test data.')
        assert_equal(set(edit['packages']), set(('warandpeace', 'annakarenina')))
        assert 'id' in edit

    def test_06_tag_list(self):
        postparams = '%s=1' % json.dumps({})
        res = self.app.post('/api/action/tag_list', params=postparams)
        assert_dicts_equal_ignoring_ordering(
            json.loads(res.body),
            {'help': 'Returns a list of tags',
             'success': True,
             'result': ['russian', 'tolstoy']})
        #Get all fields
        postparams = '%s=1' % json.dumps({'all_fields':True})
        res = self.app.post('/api/action/tag_list', params=postparams)
        res_obj = json.loads(res.body)
        pprint(res_obj)
        assert res_obj['success'] == True
        if res_obj['result'][0]['name'] == 'russian':
            russian_index = 0
            tolstoy_index = 1
        else:
            russian_index = 1
            tolstoy_index = 0
        assert res_obj['result'][russian_index]['name'] == 'russian'
        assert len(res_obj['result'][russian_index]['packages']) - \
               len(res_obj['result'][tolstoy_index]['packages']) == 1
        assert res_obj['result'][tolstoy_index]['name'] == 'tolstoy'
        assert 'id' in res_obj['result'][0]
        assert 'id' in res_obj['result'][1]

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

    def test_07_tag_show_unknown_license(self):
        # create a tagged package which has an invalid license
        CreateTestData.create_arbitrary([{
            'name': u'tag_test',
            'tags': u'tolstoy',
            'license': 'never_heard_of_it',
            }])
        postparams = '%s=1' % json.dumps({'id':'tolstoy'})
        res = self.app.post('/api/action/tag_show', params=postparams)
        res_obj = json.loads(res.body)
        assert res_obj['success'] == True
        result = res_obj['result']
        for pkg in result['packages']:
            if pkg['name'] == 'tag_test':
                break
        else:
            assert 0, 'tag_test not among packages'
        assert_equal(pkg['license_id'], 'never_heard_of_it')
        assert_equal(pkg['isopen'], False)

    def test_08_user_create_not_authorized(self):
        postparams = '%s=1' % json.dumps({'name':'test_create_from_action_api', 'password':'testpass'})
        res = self.app.post('/api/action/user_create', params=postparams,
                            status=self.STATUS_403_ACCESS_DENIED)
        res_obj = json.loads(res.body)
        assert res_obj == {'help': 'Creates a new user',
                           'success': False,
                           'error': {'message': 'Access denied', '__type': 'Authorization Error'}}

    def test_09_user_create(self):
        user_dict = {'name':'test_create_from_action_api',
                      'about': 'Just a test user',
                      'email': 'me@test.org',
                      'password':'testpass'}

        postparams = '%s=1' % json.dumps(user_dict)
        res = self.app.post('/api/action/user_create', params=postparams,
                            extra_environ={'Authorization': str(self.sysadmin_user.apikey)})
        res_obj = json.loads(res.body)
        assert res_obj['help'] == 'Creates a new user'
        assert res_obj['success'] == True
        result = res_obj['result']
        assert result['name'] == user_dict['name']
        assert result['about'] == user_dict['about']
        assert 'apikey' in result
        assert 'created' in result
        assert 'display_name' in result
        assert 'number_administered_packages' in result
        assert 'number_of_edits' in result
        assert not 'password' in result

    def test_10_user_create_parameters_missing(self):
        user_dict = {}

        postparams = '%s=1' % json.dumps(user_dict)
        res = self.app.post('/api/action/user_create', params=postparams,
                            extra_environ={'Authorization': str(self.sysadmin_user.apikey)},
                            status=self.STATUS_409_CONFLICT)
        res_obj = json.loads(res.body)
        assert res_obj == {
            'error': {
                '__type': 'Validation Error',
                'name': ['Missing value'],
                'email': ['Missing value'],
                'password': ['Missing value']
            },
            'help': 'Creates a new user',
            'success': False
        }

    def test_11_user_create_wrong_password(self):
        user_dict = {'name':'test_create_from_action_api_2',
                'email':'me@test.org',
                      'password':'tes'} #Too short

        postparams = '%s=1' % json.dumps(user_dict)
        res = self.app.post('/api/action/user_create', params=postparams,
                            extra_environ={'Authorization': str(self.sysadmin_user.apikey)},
                            status=self.STATUS_409_CONFLICT)

        res_obj = json.loads(res.body)
        assert res_obj == {
            'error': {
                '__type': 'Validation Error',
                'password': ['Your password must be 4 characters or longer']
            },
            'help': 'Creates a new user',
            'success': False
        }

    def test_12_user_update(self):
        normal_user_dict = {'id': self.normal_user.id,
                            'fullname': 'Updated normal user full name',
                            'email': 'me@test.org',
                            'about':'Updated normal user about'}

        sysadmin_user_dict = {'id': self.sysadmin_user.id,
                            'fullname': 'Updated sysadmin user full name',
                            'email': 'me@test.org',
                            'about':'Updated sysadmin user about'} 

        #Normal users can update themselves
        postparams = '%s=1' % json.dumps(normal_user_dict)
        res = self.app.post('/api/action/user_update', params=postparams,
                            extra_environ={'Authorization': str(self.normal_user.apikey)})

        res_obj = json.loads(res.body)
        assert res_obj['help'] == 'Updates the user\'s details'
        assert res_obj['success'] == True
        result = res_obj['result']
        assert result['id'] == self.normal_user.id
        assert result['name'] == self.normal_user.name
        assert result['fullname'] == normal_user_dict['fullname']
        assert result['about'] == normal_user_dict['about']
        assert 'apikey' in result
        assert 'created' in result
        assert 'display_name' in result
        assert 'number_administered_packages' in result
        assert 'number_of_edits' in result
        assert not 'password' in result

        #Sysadmin users can update themselves
        postparams = '%s=1' % json.dumps(sysadmin_user_dict)
        res = self.app.post('/api/action/user_update', params=postparams,
                            extra_environ={'Authorization': str(self.sysadmin_user.apikey)})

        res_obj = json.loads(res.body)
        assert res_obj['help'] == 'Updates the user\'s details'
        assert res_obj['success'] == True
        result = res_obj['result']
        assert result['id'] == self.sysadmin_user.id
        assert result['name'] == self.sysadmin_user.name
        assert result['fullname'] == sysadmin_user_dict['fullname']
        assert result['about'] == sysadmin_user_dict['about']

        #Sysadmin users can update all users
        postparams = '%s=1' % json.dumps(normal_user_dict)
        res = self.app.post('/api/action/user_update', params=postparams,
                            extra_environ={'Authorization': str(self.sysadmin_user.apikey)})

        res_obj = json.loads(res.body)
        assert res_obj['help'] == 'Updates the user\'s details'
        assert res_obj['success'] == True
        result = res_obj['result']
        assert result['id'] == self.normal_user.id
        assert result['name'] == self.normal_user.name
        assert result['fullname'] == normal_user_dict['fullname']
        assert result['about'] == normal_user_dict['about']

        #Normal users can not update other users
        postparams = '%s=1' % json.dumps(sysadmin_user_dict)
        res = self.app.post('/api/action/user_update', params=postparams,
                            extra_environ={'Authorization': str(self.normal_user.apikey)},
                            status=self.STATUS_403_ACCESS_DENIED)

        res_obj = json.loads(res.body)
        assert res_obj == {
            'error': {
                '__type': 'Authorization Error',
                'message': 'Access denied'
            },
            'help': 'Updates the user\'s details',
            'success': False
        }

    def test_13_group_list(self):
        postparams = '%s=1' % json.dumps({})
        res = self.app.post('/api/action/group_list', params=postparams)
        res_obj = json.loads(res.body)
        assert_dicts_equal_ignoring_ordering(
            res_obj,
            {
                'result': [
                    'david',
                    'roger'
                    ],
                'help': 'Returns a list of groups',
                'success': True
            })
        
        #Get all fields
        postparams = '%s=1' % json.dumps({'all_fields':True})
        res = self.app.post('/api/action/group_list', params=postparams)
        res_obj = json.loads(res.body)

        assert res_obj['success'] == True
        assert res_obj['result'][0]['name'] == 'david'
        assert res_obj['result'][0]['display_name'] == 'Dave\'s books'
        assert res_obj['result'][0]['packages'] == 2
        assert res_obj['result'][1]['name'] == 'roger'
        assert res_obj['result'][1]['packages'] == 1
        assert 'id' in res_obj['result'][0]
        assert 'revision_id' in res_obj['result'][0]
        assert 'state' in res_obj['result'][0]

    def test_14_group_show(self):
        postparams = '%s=1' % json.dumps({'id':'david'})
        res = self.app.post('/api/action/group_show', params=postparams)
        res_obj = json.loads(res.body)
        assert res_obj['help'] == 'Shows group details'
        assert res_obj['success'] == True
        result = res_obj['result']
        assert result['name'] == 'david'
        assert result['title'] == result['display_name'] == 'Dave\'s books'
        assert result['state'] == 'active'
        assert 'id' in result
        assert 'revision_id' in result
        assert len(result['packages']) == 2

        #Group not found
        postparams = '%s=1' % json.dumps({'id':'not_present_in_the_db'})
        res = self.app.post('/api/action/group_show', params=postparams,
                            status=self.STATUS_404_NOT_FOUND)

        res_obj = json.loads(res.body)
        pprint(res_obj)
        assert res_obj == {
            'error': {
                '__type': 'Not Found Error',
                'message': 'Not found'
            },
            'help': 'Shows group details',
            'success': False
        }

    def test_15_tag_autocomplete(self):
        #Empty query
        postparams = '%s=1' % json.dumps({})
        res = self.app.post('/api/action/tag_autocomplete', params=postparams)
        res_obj = json.loads(res.body)
        assert res_obj == {
            'help': 'Returns tags containing the provided string', 
            'result': [], 
            'success': True
        }

        #Normal query
        postparams = '%s=1' % json.dumps({'q':'r'})
        res = self.app.post('/api/action/tag_autocomplete', params=postparams)
        res_obj = json.loads(res.body)
        assert res_obj == {
            'help': 'Returns tags containing the provided string', 
            'result': ['russian'], 
            'success': True
        }

    def test_16_user_autocomplete(self):
        #Empty query
        postparams = '%s=1' % json.dumps({})
        res = self.app.post('/api/action/user_autocomplete', params=postparams)
        res_obj = json.loads(res.body)
        assert res_obj == {
            'help': 'Returns users containing the provided string', 
            'result': [], 
            'success': True
        }

        #Normal query
        postparams = '%s=1' % json.dumps({'q':'joe'})
        res = self.app.post('/api/action/user_autocomplete', params=postparams)
        res_obj = json.loads(res.body)
        assert res_obj['result'][0]['name'] == 'joeadmin'
        assert 'id','fullname' in res_obj['result'][0]

    def test_17_bad_action(self):
        #Empty query
        postparams = '%s=1' % json.dumps({})
        res = self.app.post('/api/action/bad_action_name', params=postparams,
                            status=400)
        res_obj = json.loads(res.body)
        assert_equal(res_obj, u'Bad request - Action name not known: bad_action_name')

    def test_19_update_resource(self):
        package = {
            'name': u'annakareninanew',
            'resources': [{
                'alt_url': u'alt123',
                'description': u'Full text.',
                'extras': {u'alt_url': u'alt123', u'size': u'123'},
                'format': u'plain text',
                'hash': u'abc123',
                'position': 0,
                'url': u'http://www.annakarenina.com/download/'
            }],
            'title': u'A Novel By Tolstoy',
            'url': u'http://www.annakarenina.com',
        }

        postparams = '%s=1' % json.dumps(package)
        res = self.app.post('/api/action/package_create', params=postparams,
                            extra_environ={'Authorization': 'tester'})
        package_created = json.loads(res.body)['result']

        resource_created = package_created['resources'][0]
        new_resource_url = u'http://www.annakareinanew.com/download/' 
        resource_created['url'] = new_resource_url
        postparams = '%s=1' % json.dumps(resource_created)
        res = self.app.post('/api/action/resource_update', params=postparams,
                            extra_environ={'Authorization': 'tester'})
        
        resource_updated = json.loads(res.body)['result']
        assert resource_updated['url'] == new_resource_url, resource_updated

        resource_updated.pop('url')
        resource_updated.pop('revision_id')
        resource_updated.pop('revision_timestamp')
        resource_created.pop('url')
        resource_created.pop('revision_id')
        resource_created.pop('revision_timestamp')
        assert resource_updated == resource_created
