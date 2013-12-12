import re
import json
import urllib
from pprint import pprint
from nose.tools import assert_equal, assert_raises
from nose.plugins.skip import SkipTest
from pylons import config
import datetime
import mock

import vdm.sqlalchemy
import ckan
from ckan.lib.create_test_data import CreateTestData
from ckan.lib.dictization.model_dictize import resource_dictize
import ckan.model as model
import ckan.tests as tests
from ckan.tests import WsgiAppCase
from ckan.tests.functional.api import assert_dicts_equal_ignoring_ordering
from ckan.tests import setup_test_search_index, search_related
from ckan.tests import StatusCodes
from ckan.logic import get_action, NotAuthorized
from ckan.logic.action import get_domain_object
from ckan.tests import TestRoles
import ckan.lib.search as search

from ckan import plugins
from ckan.plugins import SingletonPlugin, implements, IPackageController

class TestAction(WsgiAppCase):

    sysadmin_user = None

    normal_user = None

    @classmethod
    def setup_class(cls):
        search.clear()
        CreateTestData.create()
        cls.sysadmin_user = model.User.get('testsysadmin')
        cls.normal_user = model.User.get('annafan')
        CreateTestData.make_some_vocab_tags()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def _add_basic_package(self, package_name=u'test_package', **kwargs):
        package = {
            'name': package_name,
            'title': u'A Novel By Tolstoy',
            'resources': [{
                'description': u'Full text.',
                'format': u'plain text',
                'url': u'http://www.annakarenina.com/download/'
            }]
        }
        package.update(kwargs)

        postparams = '%s=1' % json.dumps(package)
        res = self.app.post('/api/action/package_create', params=postparams,
                            extra_environ={'Authorization': 'tester'})
        return json.loads(res.body)['result']

    def test_01_package_list(self):
        res = json.loads(self.app.post('/api/action/package_list',
                         headers={'content-type': 'application/json'}).body)
        assert res['success'] is True
        assert len(res['result']) == 2
        assert 'warandpeace' in res['result']
        assert 'annakarenina' in res['result']
        assert res['help'].startswith(
            "Return a list of the names of the site's datasets (packages).")

        postparams = '%s=1' % json.dumps({'limit': 1})
        res = json.loads(self.app.post('/api/action/package_list',
                         params=postparams).body)
        assert res['success'] is True
        assert len(res['result']) == 1
        assert 'warandpeace' in res['result'] or 'annakarenina' in res['result']

		# Test GET request
        res = json.loads(self.app.get('/api/action/package_list').body)
        assert len(res['result']) == 2
        assert 'warandpeace' in res['result']
        assert 'annakarenina' in res['result']

    def test_01_package_list_private(self):
        tests.call_action_api(self.app, 'organization_create',
                                        name='test_org_2',
                                        apikey=self.sysadmin_user.apikey)

        tests.call_action_api(self.app, 'package_create',
                                        name='public_dataset',
                                        owner_org='test_org_2',
                                        apikey=self.sysadmin_user.apikey)

        res = tests.call_action_api(self.app, 'package_list')

        assert len(res) == 3
        assert 'warandpeace' in res
        assert 'annakarenina' in res
        assert 'public_dataset' in res

        tests.call_action_api(self.app, 'package_create',
                                        name='private_dataset',
                                        owner_org='test_org_2',
                                        private=True,
                                        apikey=self.sysadmin_user.apikey)

        res = tests.call_action_api(self.app, 'package_list')
        assert len(res) == 3
        assert 'warandpeace' in res
        assert 'annakarenina' in res
        assert 'public_dataset' in res
        assert not 'private_dataset' in res

    def test_01_current_package_list_with_resources(self):
        url = '/api/action/current_package_list_with_resources'

        postparams = '%s=1' % json.dumps({
            'limit': 1,
            'offset': 1})
        res = json.loads(self.app.post(url, params=postparams).body)
        assert res['success']
        assert len(res['result']) == 1

        postparams = '%s=1' % json.dumps({
            'limit': '5'})
        res = json.loads(self.app.post(url, params=postparams).body)
        assert res['success']

        postparams = '%s=1' % json.dumps({
            'limit': -2})
        res = json.loads(self.app.post(url, params=postparams,
                         status=StatusCodes.STATUS_409_CONFLICT).body)
        assert not res['success']

        postparams = '%s=1' % json.dumps({
            'offset': 'a'})
        res = json.loads(self.app.post(url, params=postparams,
                         status=StatusCodes.STATUS_409_CONFLICT).body)
        assert not res['success']

        postparams = '%s=1' % json.dumps({
            'limit': 2,
            'page': 1})
        res = json.loads(self.app.post(url, params=postparams).body)
        assert res['success']
        assert len(res['result']) == 2

        postparams = '%s=1' % json.dumps({
            'limit': 1,
            'page': 0})
        res = json.loads(self.app.post(url,
                         params=postparams,
                         status=StatusCodes.STATUS_409_CONFLICT).body)
        assert not res['success']

    def test_01_package_show(self):
        anna_id = model.Package.by_name(u'annakarenina').id
        postparams = '%s=1' % json.dumps({'id': anna_id})
        res = self.app.post('/api/action/package_show', params=postparams)
        res_dict = json.loads(res.body)
        assert_equal(res_dict['success'], True)
        assert res_dict['help'].startswith(
            "Return the metadata of a dataset (package) and its resources.")
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
        assert res_dict['help'].startswith(
            "Return the metadata of a dataset (package) and its resources.")
        pkg = res_dict['result']
        assert_equal(pkg['name'], 'annakarenina')
        missing_keys = set(('title', 'groups')) - set(pkg.keys())
        assert not missing_keys, missing_keys

    def test_02_package_autocomplete_match_name(self):
        postparams = '%s=1' % json.dumps({'q':'war', 'limit': 5})
        res = self.app.post('/api/action/package_autocomplete', params=postparams)
        res_obj = json.loads(res.body)
        assert_equal(res_obj['success'], True)
        pprint(res_obj['result'][0]['name'])
        assert_equal(res_obj['result'][0]['name'], 'warandpeace')
        assert_equal(res_obj['result'][0]['title'], 'A Wonderful Story')
        assert_equal(res_obj['result'][0]['match_field'], 'name')
        assert_equal(res_obj['result'][0]['match_displayed'], 'warandpeace')

    def test_02_package_autocomplete_match_title(self):
        postparams = '%s=1' % json.dumps({'q':'a%20w', 'limit': 5})
        res = self.app.post('/api/action/package_autocomplete', params=postparams)
        res_obj = json.loads(res.body)
        assert_equal(res_obj['success'], True)
        pprint(res_obj['result'][0]['name'])
        assert_equal(res_obj['result'][0]['name'], 'warandpeace')
        assert_equal(res_obj['result'][0]['title'], 'A Wonderful Story')
        assert_equal(res_obj['result'][0]['match_field'], 'title')
        assert_equal(res_obj['result'][0]['match_displayed'], 'A Wonderful Story (warandpeace)')

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
                           'format': u'JSON',
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
                            extra_environ={'Authorization': str(self.sysadmin_user.apikey)})
        package_created = json.loads(res.body)['result']
        print package_created
        package_created['name'] = 'moo'
        postparams = '%s=1' % json.dumps(package_created)
        res = self.app.post('/api/action/package_update', params=postparams,
                            extra_environ={'Authorization': str(self.sysadmin_user.apikey)})

        package_updated = json.loads(res.body)['result']
        package_updated.pop('revision_id')
        package_updated.pop('revision_timestamp')
        package_updated.pop('metadata_created')
        package_updated.pop('metadata_modified')

        package_created.pop('revision_id')
        package_created.pop('revision_timestamp')
        package_created.pop('metadata_created')
        package_created.pop('metadata_modified')
        assert package_updated == package_created#, (pformat(json.loads(res.body)), pformat(package_created['result']))

    def test_03_create_private_package(self):

        # Make an organization, because private datasets must belong to one.
        organization = tests.call_action_api(self.app, 'organization_create',
                                             name='test_org',
                                             apikey=self.sysadmin_user.apikey)

        # Create a dataset without specifying visibility
        package_dict = {
            'extras': [{'key': u'original media','value': u'"book"'}],
            'license_id': u'other-open',
            'maintainer_email': None,
            'name': u'annakarenina_vis',
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
                           'format': u'JSON',
                           'hash': u'def456',
                           'position': 1,
                           'url': u'http://www.annakarenina.com/index.json'}],
            'tags': [{'name': u'russian'}, {'name': u'tolstoy'}],
            'title': u'A Novel By Tolstoy',
            'url': u'http://www.annakarenina.com',
            'owner_org': organization['id'],
            'version': u'0.7a',
        }
        package_created = tests.call_action_api(self.app, 'package_create',
                                              apikey=self.sysadmin_user.apikey,
                                              **package_dict)
        assert package_created['private'] is False

        # Create a new one, explicitly saying it is public
        package_dict['name'] = u'annakareninanew_vis_public'
        package_dict['private'] = False

        package_created_public = tests.call_action_api(self.app,
                                              'package_create',
                                              apikey=self.sysadmin_user.apikey,
                                              **package_dict)
        assert package_created_public['private'] is False

        # Create a new one, explicitly saying it is private
        package_dict['name'] = u'annakareninanew_vis_private'
        package_dict['private'] = True

        package_created_private = tests.call_action_api(self.app,
                                              'package_create',
                                              apikey=self.sysadmin_user.apikey,
                                              **package_dict)
        assert package_created_private['private'] is True


    def test_18_create_package_not_authorized(self):
        # I cannot understand the logic on this one we seem to be user
        # tester but no idea how.
        raise SkipTest

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
                                     status=StatusCodes.STATUS_403_ACCESS_DENIED)

    def test_41_create_resource(self):

        anna_id = model.Package.by_name(u'annakarenina').id
        resource = {'package_id': anna_id, 'url': 'http://new_url'}
        api_key = model.User.get('testsysadmin').apikey.encode('utf8')
        postparams = '%s=1' % json.dumps(resource)
        res = self.app.post('/api/action/resource_create', params=postparams,
                            extra_environ={'Authorization': api_key })

        resource = json.loads(res.body)['result']

        assert resource['url'] == 'http://new_url'

    def test_42_create_resource_with_error(self):

        anna_id = model.Package.by_name(u'annakarenina').id
        resource = {'package_id': anna_id, 'url': 'new_url', 'created': 'bad_date'}
        api_key = model.User.get('testsysadmin').apikey.encode('utf8')

        postparams = '%s=1' % json.dumps(resource)
        res = self.app.post('/api/action/resource_create', params=postparams,
                            extra_environ={'Authorization': api_key},
                            status=StatusCodes.STATUS_409_CONFLICT)

        assert json.loads(res.body)['error'] ==  {"__type": "Validation Error", "created": ["Date format incorrect"]}



    def test_04_user_list(self):
        # Create deleted user to make sure he won't appear in the user_list
        deleted_user = CreateTestData.create_user('deleted_user')
        deleted_user.delete()
        model.repo.commit()

        postparams = '%s=1' % json.dumps({})
        res = self.app.post('/api/action/user_list', params=postparams)
        res_obj = json.loads(res.body)
        assert res_obj['help'].startswith(
                "Return a list of the site's user accounts.")
        assert res_obj['success'] == True
        assert len(res_obj['result']) == 7
        assert res_obj['result'][0]['name'] == 'annafan'
        assert res_obj['result'][0]['about'] == 'I love reading Annakarenina. My site: http://anna.com'
        assert not 'apikey' in res_obj['result'][0]

    def test_05_user_show(self):
        # Anonymous request
        postparams = '%s=1' % json.dumps({'id':'annafan'})
        res = self.app.post('/api/action/user_show', params=postparams)
        res_obj = json.loads(res.body)
        assert res_obj['help'].startswith("Return a user account.")
        assert res_obj['success'] == True
        result = res_obj['result']
        assert result['name'] == 'annafan'
        assert result['about'] == 'I love reading Annakarenina. My site: http://anna.com'
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

        # Sysadmin user can see everyone's api key
        res = self.app.post('/api/action/user_show', params=postparams,
                            extra_environ={'Authorization': str(self.sysadmin_user.apikey)})

        res_obj = json.loads(res.body)
        result = res_obj['result']
        assert result['name'] == 'annafan'
        assert 'apikey' in result

    def test_05_user_show_edits(self):
        postparams = '%s=1' % json.dumps({'id':'tester'})
        res = self.app.post('/api/action/user_show', params=postparams)
        res_obj = json.loads(res.body)
        assert res_obj['help'].startswith("Return a user account.")
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
        assert_equal(set(edit['groups']), set(( 'roger', 'david')))
        assert_equal(edit['state'], 'active')
        assert edit['message'].startswith('Creating test data.')
        assert_equal(set(edit['packages']), set(('warandpeace', 'annakarenina')))
        assert 'id' in edit

    def test_05b_user_show_datasets(self):
        postparams = '%s=1' % json.dumps({'id':'annafan'})
        res = self.app.post('/api/action/user_show', params=postparams)
        res_obj = json.loads(res.body)
        result = res_obj['result']
        datasets = result['datasets']
        assert_equal(len(datasets), 1)
        dataset = result['datasets'][0]
        assert_equal(dataset['name'], u'annakarenina')


    def test_10_user_create_parameters_missing(self):
        user_dict = {}

        postparams = '%s=1' % json.dumps(user_dict)
        res = self.app.post('/api/action/user_create', params=postparams,
                            extra_environ={'Authorization': str(self.sysadmin_user.apikey)},
                            status=StatusCodes.STATUS_409_CONFLICT)
        res_obj = json.loads(res.body)
        assert res_obj['error'] == {
                '__type': 'Validation Error',
                'name': ['Missing value'],
                'email': ['Missing value'],
                'password': ['Missing value']
            }
        assert res_obj['help'].startswith("Create a new user.")
        assert res_obj['success'] is False

    def test_11_user_create_wrong_password(self):
        user_dict = {'name':'test_create_from_action_api_2',
                'email':'me@test.org',
                      'password':'tes'} #Too short

        postparams = '%s=1' % json.dumps(user_dict)
        res = self.app.post('/api/action/user_create', params=postparams,
                            extra_environ={'Authorization': str(self.sysadmin_user.apikey)},
                            status=StatusCodes.STATUS_409_CONFLICT)

        res_obj = json.loads(res.body)
        assert res_obj['help'].startswith('Create a new user.')
        assert res_obj['success'] is False
        assert res_obj['error'] == { '__type': 'Validation Error',
                'password': ['Your password must be 4 characters or longer']}

    def test_12_user_update(self):
        normal_user_dict = {'id': self.normal_user.id,
                            'name': self.normal_user.name,
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
        assert res_obj['help'].startswith("Update a user account.")
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
        assert res_obj['help'].startswith("Update a user account.")
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
        assert res_obj['help'].startswith("Update a user account.")
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
                            status=StatusCodes.STATUS_403_ACCESS_DENIED)

        res_obj = json.loads(res.body)
        assert res_obj['help'].startswith("Update a user account.")
        assert res_obj['error']['__type'] == 'Authorization Error'
        assert res_obj['success'] is False

    def test_12_user_update_errors(self):
        test_calls = (
            # Empty name
                {'user_dict': {'id': self.normal_user.id,
                          'name':'',
                          'email':'test@test.com'},
                 'messages': [('name','Name must be at least 2 characters long')]},

            # Invalid characters in name
                {'user_dict': {'id': self.normal_user.id,
                          'name':'i++%',
                          'email':'test@test.com'},
                 'messages': [('name','Url must be purely lowercase alphanumeric')]},
            # Existing name
                {'user_dict': {'id': self.normal_user.id,
                          'name':self.sysadmin_user.name,
                          'email':'test@test.com'},
                 'messages': [('name','That login name is not available')]},
            # Missing email
                {'user_dict': {'id': self.normal_user.id,
                          'name':self.normal_user.name},
                 'messages': [('email','Missing value')]},
                 )

        for test_call in test_calls:
            postparams = '%s=1' % json.dumps(test_call['user_dict'])
            res = self.app.post('/api/action/user_update', params=postparams,
                                extra_environ={'Authorization': str(self.normal_user.apikey)},
                                status=StatusCodes.STATUS_409_CONFLICT)
            res_obj = json.loads(res.body)
            for expected_message in test_call['messages']:
                assert expected_message[1] in ''.join(res_obj['error'][expected_message[0]])

    @mock.patch('ckan.lib.mailer.send_invite')
    def test_user_invite(self, send_invite):
        email_username = 'invited_user$ckan'
        email = '%s@email.com' % email_username
        organization_name = 'an_organization'
        CreateTestData.create_groups([{'name': organization_name}])
        role = 'member'
        organization = model.Group.get(organization_name)
        params = {'email': email,
                  'group_id': organization.id,
                  'role': role}
        postparams = '%s=1' % json.dumps(params)
        extra_environ = {'Authorization': str(self.sysadmin_user.apikey)}

        res = self.app.post('/api/action/user_invite', params=postparams,
                            extra_environ=extra_environ)

        res_obj = json.loads(res.body)
        user = model.User.get(res_obj['result']['id'])
        assert res_obj['success'] is True, res_obj
        assert user.email == email, (user.email, email)
        assert user.is_pending(), user
        expected_username = email_username.replace('$', '-')
        assert user.name.startswith(expected_username), (user.name,
                                                         expected_username)
        group_ids = user.get_group_ids(capacity=role)
        assert organization.id in group_ids, (group_ids, organization.id)
        assert send_invite.called
        assert send_invite.call_args[0][0].id == res_obj['result']['id']

    @mock.patch('ckan.lib.mailer.mail_user')
    def test_user_invite_without_email_raises_error(self, mail_user):
        user_dict = {}
        postparams = '%s=1' % json.dumps(user_dict)
        extra_environ = {'Authorization': str(self.sysadmin_user.apikey)}

        res = self.app.post('/api/action/user_invite', params=postparams,
                            extra_environ=extra_environ,
                            status=StatusCodes.STATUS_409_CONFLICT)

        res_obj = json.loads(res.body)
        assert res_obj['success'] is False, res_obj
        assert 'email' in res_obj['error'], res_obj

    @mock.patch('random.SystemRandom')
    def test_user_invite_should_work_even_if_tried_username_already_exists(self, system_random_mock):
        patcher = mock.patch('ckan.lib.mailer.mail_user')
        patcher.start()
        email = 'invited_user@email.com'
        organization_name = 'an_organization'
        CreateTestData.create_groups([{'name': organization_name}])
        role = 'member'
        organization = model.Group.get(organization_name)
        params = {'email': email,
                  'group_id': organization.id,
                  'role': role}
        postparams = '%s=1' % json.dumps(params)
        extra_environ = {'Authorization': str(self.sysadmin_user.apikey)}

        system_random_mock.return_value.random.side_effect = [1000, 1000, 2000, 3000]

        for _ in range(2):
            res = self.app.post('/api/action/user_invite', params=postparams,
                                extra_environ=extra_environ)

            res_obj = json.loads(res.body)
            assert res_obj['success'] is True, res_obj
        patcher.stop()

    def test_user_delete(self):
        name = 'normal_user'
        CreateTestData.create_user(name)
        user = model.User.get(name)
        user_dict = {'id': user.id}
        postparams = '%s=1' % json.dumps(user_dict)

        res = self.app.post('/api/action/user_delete', params=postparams,
                            extra_environ={'Authorization': str(self.sysadmin_user.apikey)})

        res_obj = json.loads(res.body)
        deleted_user = model.User.get(name)
        assert res_obj['success'] is True
        assert deleted_user.is_deleted(), deleted_user

    def test_user_delete_requires_data_dict_with_key_id(self):
        user_dict = {'name': 'normal_user'}
        postparams = '%s=1' % json.dumps(user_dict)

        res = self.app.post('/api/action/user_delete', params=postparams,
                            extra_environ={'Authorization': str(self.sysadmin_user.apikey)},
                            status=StatusCodes.STATUS_409_CONFLICT)

        res_obj = json.loads(res.body)
        assert res_obj['success'] is False
        assert res_obj['error']['id'] == ['Missing value']

    def test_13_group_list(self):
        postparams = '%s=1' % json.dumps({})
        res = self.app.post('/api/action/group_list', params=postparams)
        res_obj = json.loads(res.body)
        assert res_obj['result'] == ['david', 'roger']
        assert res_obj['success'] is True
        assert res_obj['help'].startswith(
                "Return a list of the names of the site's groups.")

        # Test GET request
        res = self.app.get('/api/action/group_list')
        res_obj = json.loads(res.body)
        assert res_obj['result'] == ['david', 'roger']

        #Get all fields
        postparams = '%s=1' % json.dumps({'all_fields':True})
        res = self.app.post('/api/action/group_list', params=postparams)
        res_obj = json.loads(res.body)

        assert res_obj['success'] == True
        assert res_obj['result'][0]['name'] == 'david'
        assert res_obj['result'][0]['display_name'] == 'Dave\'s books'
        assert res_obj['result'][0]['packages'] == 2
        assert res_obj['result'][1]['name'] == 'roger', res_obj['result'][1]
        assert res_obj['result'][1]['packages'] == 1
        assert 'id' in res_obj['result'][0]
        assert 'revision_id' in res_obj['result'][0]
        assert 'state' in res_obj['result'][0]

    def test_13_group_list_by_size(self):
        postparams = '%s=1' % json.dumps({'order_by': 'packages'})
        res = self.app.post('/api/action/group_list',
                            params=postparams)
        res_obj = json.loads(res.body)
        assert_equal(sorted(res_obj['result']), ['david','roger'])

    def test_13_group_list_by_size_all_fields(self):
        postparams = '%s=1' % json.dumps({'order_by': 'packages',
                                          'all_fields': 1})
        res = self.app.post('/api/action/group_list',
                            params=postparams)
        res_obj = json.loads(res.body)
        result = res_obj['result']
        assert_equal(len(result), 2)
        assert_equal(result[0]['name'], 'david')
        assert_equal(result[0]['packages'], 2)
        assert_equal(result[1]['name'], 'roger')
        assert_equal(result[1]['packages'], 1)

    def test_14_group_show(self):
        postparams = '%s=1' % json.dumps({'id':'david'})
        res = self.app.post('/api/action/group_show', params=postparams)
        res_obj = json.loads(res.body)
        assert res_obj['help'].startswith("Return the details of a group.")
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
                            status=StatusCodes.STATUS_404_NOT_FOUND)

        res_obj = json.loads(res.body)
        pprint(res_obj)
        assert res_obj['error'] == {
                '__type': 'Not Found Error',
                'message': 'Not found'
            }
        assert res_obj['help'].startswith('Return the details of a group.')
        assert res_obj['success'] is False

    def test_16_user_autocomplete(self):
        # Create deleted user to make sure he won't appear in the user_list
        deleted_user = CreateTestData.create_user('joe')
        deleted_user.delete()
        model.repo.commit()

        #Empty query
        postparams = '%s=1' % json.dumps({})
        res = self.app.post(
            '/api/action/user_autocomplete',
            params=postparams,
            status=StatusCodes.STATUS_409_CONFLICT)
        res_obj = json.loads(res.body)
        assert res_obj['help'].startswith(
                "Return a list of user names that contain a string.")
        assert res_obj['success'] is False

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
                            extra_environ={'Authorization': str(self.sysadmin_user.apikey)})
        package_created = json.loads(res.body)['result']

        resource_created = package_created['resources'][0]
        new_resource_url = u'http://www.annakareinanew.com/download/'
        resource_created['url'] = new_resource_url
        postparams = '%s=1' % json.dumps(resource_created)
        res = self.app.post('/api/action/resource_update', params=postparams,
                            extra_environ={'Authorization': str(self.sysadmin_user.apikey)})

        resource_updated = json.loads(res.body)['result']
        assert resource_updated['url'] == new_resource_url, resource_updated

        resource_updated.pop('url')
        resource_updated.pop('revision_id')
        resource_updated.pop('revision_timestamp', None)
        resource_created.pop('url')
        resource_created.pop('revision_id')
        resource_created.pop('revision_timestamp', None)
        assert_equal(resource_updated, resource_created)

    def test_20_task_status_update(self):
        package_created = self._add_basic_package(u'test_task_status_update')

        task_status = {
            'entity_id': package_created['id'],
            'entity_type': u'package',
            'task_type': u'test_task',
            'key': u'test_key',
            'value': u'test_value',
            'state': u'test_state',
            'error': u'test_error',
        }
        postparams = '%s=1' % json.dumps(task_status)
        res = self.app.post(
            '/api/action/task_status_update', params=postparams,
            extra_environ={'Authorization': str(self.sysadmin_user.apikey)},
        )
        task_status_updated = json.loads(res.body)['result']

        task_status_id = task_status_updated.pop('id')
        task_status_updated.pop('last_updated')
        assert task_status_updated == task_status, (task_status_updated, task_status)

        task_status_updated['id'] = task_status_id
        task_status_updated['value'] = u'test_value_2'
        postparams = '%s=1' % json.dumps(task_status_updated)
        res = self.app.post(
            '/api/action/task_status_update', params=postparams,
            extra_environ={'Authorization': str(self.sysadmin_user.apikey)},
        )
        task_status_updated_2 = json.loads(res.body)['result']
        task_status_updated_2.pop('last_updated')
        assert task_status_updated_2 == task_status_updated, task_status_updated_2

    def test_21_task_status_update_many(self):
        package_created = self._add_basic_package(u'test_task_status_update_many')
        task_statuses = {
            'data': [
                {
                    'entity_id': package_created['id'],
                    'entity_type': u'package',
                    'task_type': u'test_task',
                    'key': u'test_task_1',
                    'value': u'test_value_1',
                    'state': u'test_state',
                    'error': u'test_error'
                },
                {
                    'entity_id': package_created['id'],
                    'entity_type': u'package',
                    'task_type': u'test_task',
                    'key': u'test_task_2',
                    'value': u'test_value_2',
                    'state': u'test_state',
                    'error': u'test_error'
                }
            ]
        }
        postparams = '%s=1' % json.dumps(task_statuses)
        res = self.app.post(
            '/api/action/task_status_update_many', params=postparams,
            extra_environ={'Authorization': str(self.sysadmin_user.apikey)},
        )
        task_statuses_updated = json.loads(res.body)['result']['results']
        for i in range(len(task_statuses['data'])):
            task_status = task_statuses['data'][i]
            task_status_updated = task_statuses_updated[i]
            task_status_updated.pop('id')
            task_status_updated.pop('last_updated')
            assert task_status == task_status_updated, (task_status_updated, task_status, i)

    def test_22_task_status_normal_user_not_authorized(self):
        task_status = {}
        postparams = '%s=1' % json.dumps(task_status)
        res = self.app.post(
            '/api/action/task_status_update', params=postparams,
            extra_environ={'Authorization': str(self.normal_user.apikey)},
            status=StatusCodes.STATUS_403_ACCESS_DENIED
        )
        res_obj = json.loads(res.body)
        assert res_obj['help'].startswith("Update a task status.")
        assert res_obj['success'] is False
        assert res_obj['error']['__type'] == 'Authorization Error'

    def test_23_task_status_validation(self):
        task_status = {}
        postparams = '%s=1' % json.dumps(task_status)
        res = self.app.post(
            '/api/action/task_status_update', params=postparams,
            extra_environ={'Authorization': str(self.sysadmin_user.apikey)},
            status=StatusCodes.STATUS_409_CONFLICT
        )

    def test_24_task_status_show(self):
        package_created = self._add_basic_package(u'test_task_status_show')

        task_status = {
            'entity_id': package_created['id'],
            'entity_type': u'package',
            'task_type': u'test_task',
            'key': u'test_task_status_show',
            'value': u'test_value',
            'state': u'test_state',
            'error': u'test_error'
        }
        postparams = '%s=1' % json.dumps(task_status)
        res = self.app.post(
            '/api/action/task_status_update', params=postparams,
            extra_environ={'Authorization': str(self.sysadmin_user.apikey)},
        )
        task_status_updated = json.loads(res.body)['result']

        # make sure show works when giving a task status ID
        postparams = '%s=1' % json.dumps({'id': task_status_updated['id']})
        res = self.app.post(
            '/api/action/task_status_show', params=postparams,
            extra_environ={'Authorization': str(self.sysadmin_user.apikey)},
        )
        task_status_show = json.loads(res.body)['result']

        task_status_show.pop('last_updated')
        task_status_updated.pop('last_updated')
        assert task_status_show == task_status_updated, (task_status_show, task_status_updated)

        # make sure show works when giving a (entity_id, task_type, key) tuple
        postparams = '%s=1' % json.dumps({
            'entity_id': task_status['entity_id'],
            'task_type': task_status['task_type'],
            'key': task_status['key']
        })
        res = self.app.post(
            '/api/action/task_status_show', params=postparams,
            extra_environ={'Authorization': str(self.sysadmin_user.apikey)},
        )
        task_status_show = json.loads(res.body)['result']

        task_status_show.pop('last_updated')
        assert task_status_show == task_status_updated, (task_status_show, task_status_updated)

    def test_25_task_status_delete(self):
        package_created = self._add_basic_package(u'test_task_status_delete')

        task_status = {
            'entity_id': package_created['id'],
            'entity_type': u'package',
            'task_type': u'test_task',
            'key': u'test_task_status_delete',
            'value': u'test_value',
            'state': u'test_state',
            'error': u'test_error'
        }
        postparams = '%s=1' % json.dumps(task_status)
        res = self.app.post(
            '/api/action/task_status_update', params=postparams,
            extra_environ={'Authorization': str(self.sysadmin_user.apikey)},
        )
        task_status_updated = json.loads(res.body)['result']

        postparams = '%s=1' % json.dumps({'id': task_status_updated['id']})
        res = self.app.post(
            '/api/action/task_status_delete', params=postparams,
            extra_environ={'Authorization': str(self.sysadmin_user.apikey)},
        )
        task_status_delete = json.loads(res.body)
        assert task_status_delete['success'] == True

    def test_26_resource_show(self):
        pkg = model.Package.get('annakarenina')
        resource = pkg.resources[0]
        postparams = '%s=1' % json.dumps({'id': resource.id})
        res = self.app.post('/api/action/resource_show', params=postparams)
        result = json.loads(res.body)['result']

        # Remove tracking data from the result dict. This tracking data is
        # added by the logic, so the other resource dict taken straight from
        # resource_dictize() won't have it.
        del result['tracking_summary']

        resource_dict = resource_dictize(resource, {'model': model})
        assert result == resource_dict, (result, resource_dict)

    def test_27_get_site_user_not_authorized(self):
        assert_raises(NotAuthorized,
                     get_action('get_site_user'),
                     {'model': model}, {})
        user = model.User.get('test.ckan.net')
        assert not user

        site_id = config.get('ckan.site_id')
        user = get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})
        assert user['name'] == site_id

        user = model.User.get(site_id)
        assert user

        user=get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})
        assert user['name'] == site_id

        user = model.Session.query(model.User).filter_by(name=site_id).one()
        assert user

    def test_28_group_package_show(self):
        group_id = model.Group.get('david').id
        group_packages = get_action('group_package_show')(
            {'model': model, 'user': self.normal_user.name, 'ignore_auth': True},
            {'id': group_id}
        )
        assert len(group_packages) == 2, group_packages
        group_names = set([g.get('name') for g in group_packages])
        assert group_names == set(['annakarenina', 'warandpeace']), group_names

    def test_29_group_package_show_pending(self):
        context = {'model': model, 'session': model.Session, 'user': self.sysadmin_user.name, 'api_version': 2, 'ignore_auth': True}
        group = {
            'name': 'test_group_pending_package',
            'packages': [{'id': model.Package.get('annakarenina').id}]
        }
        group = get_action('group_create')(context, group)

        pkg = {
            'name': 'test_pending_package',
            'groups': [{'id': group['id']}]
        }
        pkg = get_action('package_create')(context, pkg)
        # can't seem to add a package with 'pending' state, so update it
        pkg['state'] = 'pending'
        get_action('package_update')(context, pkg)

        group_packages = get_action('group_package_show')(context, {'id': group['id']})
        assert len(group_packages) == 2, (len(group_packages), group_packages)
        group_names = set([g.get('name') for g in group_packages])
        assert group_names == set(['annakarenina', 'test_pending_package']), group_names

        get_action('group_delete')(context, group)
        get_action('package_delete')(context, pkg)

    def test_30_status_show(self):
        postparams = '%s=1' % json.dumps({})
        res = self.app.post('/api/action/status_show', params=postparams)
        status = json.loads(res.body)['result']
        assert_equal(status['site_title'], 'CKAN')
        assert_equal(status['ckan_version'], ckan.__version__)
        assert_equal(status['site_url'], 'http://test.ckan.net')

    def test_31_bad_request_format(self):
        postparams = '%s=1' % json.dumps('not a dict')
        res = self.app.post('/api/action/package_list', params=postparams,
                            status=400)
        assert "Bad request - JSON Error: Request data JSON decoded to 'not a dict' but it needs to be a dictionary." in res.body, res.body

    def test_31_bad_request_format_not_json(self):
        postparams = '=1'
        res = self.app.post('/api/action/package_list', params=postparams,
                            status=400)
        assert "Bad request - Bad request data: Request data JSON decoded to '' but it needs to be a dictionary." in res.body, res.body

    def test_32_get_domain_object(self):
        anna = model.Package.by_name(u'annakarenina')
        assert_equal(get_domain_object(model, anna.name).name, anna.name)
        assert_equal(get_domain_object(model, anna.id).name, anna.name)
        group = model.Group.by_name(u'david')
        assert_equal(get_domain_object(model, group.name).name, group.name)
        assert_equal(get_domain_object(model, group.id).name, group.name)

    def test_33_roles_show(self):
        anna = model.Package.by_name(u'annakarenina')
        annafan = model.User.by_name(u'annafan')
        postparams = '%s=1' % json.dumps({'domain_object': anna.id})
        res = self.app.post('/api/action/roles_show', params=postparams,
                            extra_environ={'Authorization': str(annafan.apikey)},
                            status=200)
        results = json.loads(res.body)['result']
        anna = model.Package.by_name(u'annakarenina')
        assert_equal(results['domain_object_id'], anna.id)
        assert_equal(results['domain_object_type'], 'Package')
        roles = results['roles']
        assert len(roles) > 2, results
        assert set(roles[0].keys()) > set(('user_id', 'package_id', 'role',
                                           'context', 'user_object_role_id'))

    def test_34_roles_show_for_user(self):
        anna = model.Package.by_name(u'annakarenina')
        annafan = model.User.by_name(u'annafan')
        postparams = '%s=1' % json.dumps({'domain_object': anna.id,
                                          'user': 'annafan'})
        res = self.app.post('/api/action/roles_show', params=postparams,
                            extra_environ={'Authorization': str(annafan.apikey)},
                            status=200)
        results = json.loads(res.body)['result']
        anna = model.Package.by_name(u'annakarenina')
        assert_equal(results['domain_object_id'], anna.id)
        assert_equal(results['domain_object_type'], 'Package')
        roles = results['roles']
        assert_equal(len(roles), 1)
        assert set(roles[0].keys()) > set(('user_id', 'package_id', 'role',
                                           'context', 'user_object_role_id'))


    def test_35_user_role_update(self):
        anna = model.Package.by_name(u'annakarenina')
        annafan = model.User.by_name(u'annafan')
        roles_before = get_action('roles_show') \
                                 ({'model': model, 'session': model.Session}, \
                                  {'domain_object': anna.id,
                                   'user': 'tester'})
        postparams = '%s=1' % json.dumps({'user': 'tester',
                                          'domain_object': anna.id,
                                          'roles': ['reader']})

        res = self.app.post('/api/action/user_role_update', params=postparams,
                            extra_environ={'Authorization': str(annafan.apikey)},
                            status=200)
        results = json.loads(res.body)['result']
        assert_equal(len(results['roles']), 1)
        anna = model.Package.by_name(u'annakarenina')
        tester = model.User.by_name(u'tester')
        assert_equal(results['roles'][0]['role'], 'reader')
        assert_equal(results['roles'][0]['package_id'], anna.id)
        assert_equal(results['roles'][0]['user_id'], tester.id)

        roles_after = get_action('roles_show') \
                      ({'model': model, 'session': model.Session}, \
                       {'domain_object': anna.id,
                        'user': 'tester'})
        assert_equal(results['roles'], roles_after['roles'])


    def test_37_user_role_update_disallowed(self):
        # Roles are no longer used so ignore this test
        raise SkipTest
        anna = model.Package.by_name(u'annakarenina')
        postparams = '%s=1' % json.dumps({'user': 'tester',
                                          'domain_object': anna.id,
                                          'roles': ['editor']})
        # tester has no admin priviledges for this package
        res = self.app.post('/api/action/user_role_update', params=postparams,
                            extra_environ={'Authorization': 'tester'},
                            status=403)

    def test_38_user_role_bulk_update(self):
        anna = model.Package.by_name(u'annakarenina')
        annafan = model.User.by_name(u'annafan')
        all_roles_before = TestRoles.get_roles(anna.id)
        user_roles_before = TestRoles.get_roles(anna.id, user_ref=annafan.name)
        roles_before = get_action('roles_show') \
                                 ({'model': model, 'session': model.Session}, \
                                  {'domain_object': anna.id})
        postparams = '%s=1' % json.dumps({'domain_object': anna.id,
                                          'user_roles': [
                    {'user': 'annafan',
                     'roles': ('admin', 'editor')},
                    {'user': 'russianfan',
                     'roles': ['editor']},
                                              ]})

        res = self.app.post('/api/action/user_role_bulk_update', params=postparams,
                            extra_environ={'Authorization': str(annafan.apikey)},
                            status=200)
        results = json.loads(res.body)['result']

        # check there are 2 new roles (not 3 because annafan is already admin)
        all_roles_after = TestRoles.get_roles(anna.id)
        user_roles_after = TestRoles.get_roles(anna.id, user_ref=annafan.name)
        assert_equal(set(all_roles_before) ^ set(all_roles_after),
                     set([u'"annafan" is "editor" on "annakarenina"',
                          u'"russianfan" is "editor" on "annakarenina"']))

        roles_after = get_action('roles_show') \
                      ({'model': model, 'session': model.Session}, \
                       {'domain_object': anna.id})
        assert_equal(results['roles'], roles_after['roles'])

    def test_40_task_resource_status(self):

        try:
            import ckan.lib.celery_app as celery_app
        except ImportError:
            raise SkipTest('celery not installed')

        backend = celery_app.celery.backend
        ##This creates the database tables as a side effect, can not see another way
        ##to make tables unless you actually create a task.
        celery_result_session = backend.ResultSession()

        ## need to do inserts as setting up an embedded celery is too much for these tests
        model.Session.connection().execute(
            '''INSERT INTO task_status (id, entity_id, entity_type, task_type, key, value, state, error, last_updated) VALUES ('5753adae-cd0d-4327-915d-edd832d1c9a3', '749cdcf2-3fc8-44ae-aed0-5eff8cc5032c', 'resource', 'qa', 'celery_task_id', '51f2105d-85b1-4393-b821-ac11475919d9', NULL, '', '2012-04-20 21:32:45.553986');
               INSERT INTO celery_taskmeta (id, task_id, status, result, date_done, traceback) VALUES (2, '51f2105d-85b1-4393-b821-ac11475919d9', 'FAILURE', '52e', '2012-04-20 21:33:01.622557', 'Traceback')'''
        )
        model.Session.commit()
        res = json.loads(self.app.post('/api/action/resource_status_show',
                            params=json.dumps({'id': '749cdcf2-3fc8-44ae-aed0-5eff8cc5032c'}),
                            status=200).body)

        assert res['help'].startswith(
                "Return the statuses of a resource's tasks.")
        assert res['success'] is True
        assert res['result'] == [{"status": "FAILURE", "entity_id": "749cdcf2-3fc8-44ae-aed0-5eff8cc5032c", "task_type": "qa", "last_updated": "2012-04-20T21:32:45.553986", "date_done": "2012-04-20T21:33:01.622557", "entity_type": "resource", "traceback": "Traceback", "value": "51f2105d-85b1-4393-b821-ac11475919d9", "state": None, "key": "celery_task_id", "error": "", "id": "5753adae-cd0d-4327-915d-edd832d1c9a3"}]

    def test_41_missing_action(self):
        try:
            get_action('unicorns')
            assert False, "We found a non-existent action"
        except KeyError:
            assert True

    def test_42_resource_search_with_single_field_query(self):
        request_body = {
            'query': ["description:index"],
        }
        postparams = json.dumps(request_body)
        response = self.app.post('/api/action/resource_search',
                                 params=postparams)
        result = json.loads(response.body)['result']['results']
        count = json.loads(response.body)['result']['count']

        ## Due to the side-effect of previously run tests, there may be extra
        ## resources in the results.  So just check that each found Resource
        ## matches the search criteria
        assert count > 0
        for resource in result:
            assert "index" in resource['description'].lower()

    def test_42_resource_search_across_multiple_fields(self):
        request_body = {
            'query': ["description:index", "format:json"],
        }
        postparams = json.dumps(request_body)
        response = self.app.post('/api/action/resource_search',
                                 params=postparams)
        result = json.loads(response.body)['result']['results']
        count = json.loads(response.body)['result']['count']

        ## Due to the side-effect of previously run tests, there may be extra
        ## resources in the results.  So just check that each found Resource
        ## matches the search criteria
        assert count > 0
        for resource in result:
            assert "index" in resource['description'].lower()
            assert "json" in resource['format'].lower()

    def test_42_resource_search_test_percentage_is_escaped(self):
        request_body = {
            'query': ["description:index%"],
        }
        postparams = json.dumps(request_body)
        response = self.app.post('/api/action/resource_search',
                                 params=postparams)
        count = json.loads(response.body)['result']['count']

        # There shouldn't be any results.  If the '%' character wasn't
        # escaped correctly, then the search would match because of the
        # unescaped wildcard.
        assert count is 0

    def test_42_resource_search_fields_parameter_still_accepted(self):
        '''The fields parameter is deprecated, but check it still works.

        Remove this test when removing the fields parameter.  (#2603)
        '''
        request_body = {
            'fields': {"description": "index"},
        }

        postparams = json.dumps(request_body)
        response = self.app.post('/api/action/resource_search',
                                 params=postparams)
        result = json.loads(response.body)['result']['results']
        count = json.loads(response.body)['result']['count']

        ## Due to the side-effect of previously run tests, there may be extra
        ## resources in the results.  So just check that each found Resource
        ## matches the search criteria
        assert count > 0
        for resource in result:
            assert "index" in resource['description'].lower()

    def test_42_resource_search_accessible_via_get_request(self):
        response = self.app.get('/api/action/resource_search'
                                '?query=description:index&query=format:json')

        result = json.loads(response.body)['result']['results']
        count = json.loads(response.body)['result']['count']

        ## Due to the side-effect of previously run tests, there may be extra
        ## resources in the results.  So just check that each found Resource
        ## matches the search criteria
        assert count > 0
        for resource in result:
            assert "index" in resource['description'].lower()
            assert "json" in resource['format'].lower()

    def test_package_create_duplicate_extras_error(self):
        import ckan.tests
        import paste.fixture
        import pylons.test

        # Posting a dataset dict to package_create containing two extras dicts
        # with the same key, should return a Validation Error.
        app = paste.fixture.TestApp(pylons.test.pylonsapp)
        error = ckan.tests.call_action_api(app, 'package_create',
                apikey=self.sysadmin_user.apikey, status=409,
                name='foobar', extras=[{'key': 'foo', 'value': 'bar'},
                    {'key': 'foo', 'value': 'gar'}])
        assert error['__type'] == 'Validation Error'
        assert error['extras_validation'] == ['Duplicate key "foo"']

    def test_package_update_remove_org_error(self):
        import ckan.tests
        import paste.fixture
        import pylons.test

        app = paste.fixture.TestApp(pylons.test.pylonsapp)
        org = ckan.tests.call_action_api(app, 'organization_create',
                apikey=self.sysadmin_user.apikey, name='myorganization')
        package = ckan.tests.call_action_api(app, 'package_create',
                apikey=self.sysadmin_user.apikey, name='foobarbaz', owner_org=org['id'])

        assert package['owner_org']
        package['owner_org'] = ''
        res = ckan.tests.call_action_api(app, 'package_update',
                apikey=self.sysadmin_user.apikey, **package)
        assert not res['owner_org'], res['owner_org']

    def test_package_update_duplicate_extras_error(self):
        import ckan.tests
        import paste.fixture
        import pylons.test

        # We need to create a package first, so that we can update it.
        app = paste.fixture.TestApp(pylons.test.pylonsapp)
        package = ckan.tests.call_action_api(app, 'package_create',
                apikey=self.sysadmin_user.apikey, name='foobar')

        # Posting a dataset dict to package_update containing two extras dicts
        # with the same key, should return a Validation Error.
        package['extras'] = [{'key': 'foo', 'value': 'bar'},
                    {'key': 'foo', 'value': 'gar'}]
        error = ckan.tests.call_action_api(app, 'package_update',
                apikey=self.sysadmin_user.apikey, status=409, **package)
        assert error['__type'] == 'Validation Error'
        assert error['extras_validation'] == ['Duplicate key "foo"']

class TestActionTermTranslation(WsgiAppCase):

    @classmethod
    def setup_class(self):
        CreateTestData.create()
        self.sysadmin_user = model.User.get('testsysadmin')
        self.normal_user = model.User.get('annafan')

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_1_update_single(self):
        postparams = '%s=1' % json.dumps(
            {"term" : "moo",
             "term_translation": "moo",
             "lang_code" : "fr"
            }
        )

        res = self.app.post('/api/action/term_translation_update', params=postparams,
                            extra_environ={'Authorization': str(self.sysadmin_user.apikey)},
                            status=200)

        assert json.loads(res.body)['success']

        postparams = '%s=1' % json.dumps(
            {"term" : "moo",
             "term_translation": "moomoo",
             "lang_code" : "fr"
            }
        )

        res = self.app.post('/api/action/term_translation_update', params=postparams,
                            extra_environ={'Authorization': str(self.sysadmin_user.apikey)},
                            status=200)

        assert json.loads(res.body)['success']

        postparams = '%s=1' % json.dumps(
            {"term" : "moo",
             "term_translation": "moomoo",
             "lang_code" : "en"
            }
        )

        res = self.app.post('/api/action/term_translation_update', params=postparams,
                            extra_environ={'Authorization': str(self.sysadmin_user.apikey)},
                            status=200)

        assert json.loads(res.body)['success']

        postparams = '%s=1' % json.dumps({"terms" : ["moo"]})

        res = self.app.post('/api/action/term_translation_show', params=postparams,
                            extra_environ={'Authorization': str(self.sysadmin_user.apikey)},
                            status=200)

        assert json.loads(res.body)['success']
        assert json.loads(res.body)['result'] == [{u'lang_code': u'fr', u'term': u'moo', u'term_translation': u'moomoo'},
                                                  {u'lang_code': u'en', u'term': u'moo', u'term_translation': u'moomoo'}], json.loads(res.body)

    def test_2_update_many(self):

        postparams = '%s=1' % json.dumps({'data': [
             {"term" : "many",
              "term_translation": "manymoo",
              "lang_code" : "fr"
             },
             {"term" : "many",
              "term_translation": "manymoo",
              "lang_code" : "en"
             },
             {"term" : "many",
              "term_translation": "manymoomoo",
              "lang_code" : "en"
             }
            ]
        }
        )
        res = self.app.post('/api/action/term_translation_update_many', params=postparams,
                            extra_environ={'Authorization': str(self.sysadmin_user.apikey)},
                            status=200)

        assert json.loads(res.body)['result']['success'] == '3 rows updated', json.loads(res.body)

        postparams = '%s=1' % json.dumps({"terms" : ["many"]})
        res = self.app.post('/api/action/term_translation_show', params=postparams,
                            extra_environ={'Authorization': str(self.sysadmin_user.apikey)},
                            status=200)

        assert json.loads(res.body)['result'] == [{u'lang_code': u'fr', u'term': u'many', u'term_translation': u'manymoo'},
                                                  {u'lang_code': u'en', u'term': u'many', u'term_translation': u'manymoomoo'}], json.loads(res.body)




class TestActionPackageSearch(WsgiAppCase):

    @classmethod
    def setup_class(cls):
        setup_test_search_index()
        CreateTestData.create()
        cls.sysadmin_user = model.User.get('testsysadmin')

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_1_basic(self):
        params = {
                'q':'tolstoy',
                'facet.field': ['groups', 'tags', 'res_format', 'license'],
                'rows': 20,
                'start': 0,
            }
        postparams = '%s=1' % json.dumps(params)
        res = self.app.post('/api/action/package_search', params=postparams)
        res = json.loads(res.body)
        result = res['result']
        assert_equal(res['success'], True)
        assert_equal(result['count'], 1)
        assert_equal(result['results'][0]['name'], 'annakarenina')

        # Test GET request
        params_json_list = params
        params_json_list['facet.field'] = json.dumps(params['facet.field'])
        url_params = urllib.urlencode(params_json_list)
        res = self.app.get('/api/action/package_search?{0}'.format(url_params))
        res = json.loads(res.body)
        result = res['result']
        assert_equal(res['success'], True)
        assert_equal(result['count'], 1)
        assert_equal(result['results'][0]['name'], 'annakarenina')

    def test_1_facet_limit(self):
        params = {
                'q':'*:*',
                'facet.field': ['groups', 'tags', 'res_format', 'license'],
                'rows': 20,
                'start': 0,
            }
        postparams = '%s=1' % json.dumps(params)
        res = self.app.post('/api/action/package_search', params=postparams)
        res = json.loads(res.body)
        assert_equal(res['success'], True)

        assert_equal(len(res['result']['search_facets']['groups']['items']), 2)

        params = {
                'q':'*:*',
                'facet.field': ['groups', 'tags', 'res_format', 'license'],
                'facet.limit': 1,
                'rows': 20,
                'start': 0,
            }
        postparams = '%s=1' % json.dumps(params)
        res = self.app.post('/api/action/package_search', params=postparams)
        res = json.loads(res.body)
        assert_equal(res['success'], True)

        assert_equal(len(res['result']['search_facets']['groups']['items']), 1)

        params = {
                'q':'*:*',
                'facet.field': ['groups', 'tags', 'res_format', 'license'],
                'facet.limit': -1, # No limit
                'rows': 20,
                'start': 0,
            }
        postparams = '%s=1' % json.dumps(params)
        res = self.app.post('/api/action/package_search', params=postparams)
        res = json.loads(res.body)
        assert_equal(res['success'], True)

        assert_equal(len(res['result']['search_facets']['groups']['items']), 2)

    def test_1_basic_no_params(self):
        postparams = '%s=1' % json.dumps({})
        res = self.app.post('/api/action/package_search', params=postparams)
        res = json.loads(res.body)
        result = res['result']
        assert_equal(res['success'], True)
        assert_equal(result['count'], 2)
        assert result['results'][0]['name'] in ('annakarenina', 'warandpeace')

        # Test GET request
        res = self.app.get('/api/action/package_search')
        res = json.loads(res.body)
        result = res['result']
        assert_equal(res['success'], True)
        assert_equal(result['count'], 2)
        assert result['results'][0]['name'] in ('annakarenina', 'warandpeace')

    def test_2_bad_param(self):
        postparams = '%s=1' % json.dumps({
                'sort':'metadata_modified',
            })
        res = self.app.post('/api/action/package_search', params=postparams,
                            status=409)
        assert '"message": "Search error:' in res.body, res.body
        assert 'SOLR returned an error' in res.body, res.body
        # solr error is 'Missing sort order' or 'Missing_sort_order',
        # depending on the solr version.
        assert 'sort' in res.body, res.body

    def test_3_bad_param(self):
        postparams = '%s=1' % json.dumps({
                'weird_param':True,
            })
        res = self.app.post('/api/action/package_search', params=postparams,
                            status=400)
        assert '"message": "Search Query is invalid:' in res.body, res.body
        assert '"Invalid search parameters: [\'weird_param\']' in res.body, res.body

    def test_4_sort_by_metadata_modified(self):
        search_params = '%s=1' % json.dumps({
            'q': '*:*',
            'fl': 'name, metadata_modified',
            'sort': u'metadata_modified desc'
        })

        # modify warandpeace, check that it is the first search result
        rev = model.repo.new_revision()
        pkg = model.Package.get('warandpeace')
        pkg.title = "War and Peace [UPDATED]"

        pkg.metadata_modified = datetime.datetime.utcnow()
        model.repo.commit_and_remove()

        res = self.app.post('/api/action/package_search', params=search_params)
        result = json.loads(res.body)['result']
        result_names = [r['name'] for r in result['results']]
        assert result_names == ['warandpeace', 'annakarenina'], result_names

        # modify annakarenina, check that it is the first search result
        rev = model.repo.new_revision()
        pkg = model.Package.get('annakarenina')
        pkg.title = "A Novel By Tolstoy [UPDATED]"
        pkg.metadata_modified = datetime.datetime.utcnow()
        model.repo.commit_and_remove()

        res = self.app.post('/api/action/package_search', params=search_params)
        result = json.loads(res.body)['result']
        result_names = [r['name'] for r in result['results']]
        assert result_names == ['annakarenina', 'warandpeace'], result_names

        # add a tag to warandpeace, check that it is the first result
        pkg = model.Package.get('warandpeace')
        pkg_params = '%s=1' % json.dumps({'id': pkg.id})
        res = self.app.post('/api/action/package_show', params=pkg_params)
        pkg_dict = json.loads(res.body)['result']
        pkg_dict['tags'].append({'name': 'new-tag'})
        pkg_params = '%s=1' % json.dumps(pkg_dict)
        res = self.app.post('/api/action/package_update', params=pkg_params,
                            extra_environ={'Authorization':  str(self.sysadmin_user.apikey)})

        res = self.app.post('/api/action/package_search', params=search_params)
        result = json.loads(res.body)['result']
        result_names = [r['name'] for r in result['results']]
        assert result_names == ['warandpeace', 'annakarenina'], result_names

class MockPackageSearchPlugin(SingletonPlugin):
    implements(IPackageController, inherit=True)

    def before_index(self, data_dict):
        data_dict['extras_test'] = 'abcabcabc'
        return data_dict

    def before_search(self, search_params):
        if 'extras' in search_params and 'ext_avoid' in search_params['extras']:
            assert 'q' in search_params

        if 'extras' in search_params and 'ext_abort' in search_params['extras']:
            assert 'q' in search_params
            # Prevent the actual query
            search_params['abort_search'] = True

        return search_params

    def after_search(self, search_results, search_params):

        assert 'results' in search_results
        assert 'count' in search_results
        assert 'search_facets' in search_results

        if 'extras' in search_params and 'ext_avoid' in search_params['extras']:
            # Remove results with a certain value
            avoid = search_params['extras']['ext_avoid']

            for i,result in enumerate(search_results['results']):
                if avoid.lower() in result['name'].lower() or avoid.lower() in result['title'].lower():
                    search_results['results'].pop(i)
                    search_results['count'] -= 1

        return search_results

    def before_view(self, data_dict):

        data_dict['title'] = 'string_not_found_in_rest_of_template'

        return data_dict

MockPackageSearchPlugin().disable()

class TestSearchPluginInterface(WsgiAppCase):

    @classmethod
    def setup_class(cls):
        MockPackageSearchPlugin().activate()
        MockPackageSearchPlugin().enable()
        setup_test_search_index()
        CreateTestData.create()
        MockPackageSearchPlugin().disable()
        cls.sysadmin_user = model.User.get('testsysadmin')

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def setup(self):
        MockPackageSearchPlugin().enable()

    def teardown(self):
        MockPackageSearchPlugin().disable()

    def test_search_plugin_interface_search(self):
        avoid = 'Tolstoy'
        search_params = '%s=1' % json.dumps({
            'q': '*:*',
            'extras' : {'ext_avoid':avoid}
        })

        res = self.app.post('/api/action/package_search', params=search_params)

        results_dict = json.loads(res.body)['result']
        for result in results_dict['results']:
            assert not avoid.lower() in result['title'].lower()

        assert results_dict['count'] == 1

    def test_search_plugin_interface_abort(self):

        search_params = '%s=1' % json.dumps({
            'q': '*:*',
            'extras' : {'ext_abort':True}
        })

        res = self.app.post('/api/action/package_search', params=search_params)

        # Check that the query was aborted and no results returned
        res_dict = json.loads(res.body)['result']
        assert res_dict['count'] == 0
        assert len(res_dict['results']) == 0

    def test_before_index(self):

        # no datasets get aaaaaaaa
        search_params = '%s=1' % json.dumps({
            'q': 'aaaaaaaa',
        })

        res = self.app.post('/api/action/package_search', params=search_params)

        res_dict = json.loads(res.body)['result']
        assert res_dict['count'] == 0
        assert len(res_dict['results']) == 0

        # all datasets should get abcabcabc
        search_params = '%s=1' % json.dumps({
            'q': 'abcabcabc',
        })
        res = self.app.post('/api/action/package_search', params=search_params)

        res_dict = json.loads(res.body)['result']
        assert res_dict['count'] == 2, res_dict['count']
        assert len(res_dict['results']) == 2

    def test_before_view(self):
        res = self.app.get('/dataset/annakarenina')

        assert 'string_not_found_in_rest_of_template' in res.body

        res = self.app.get('/dataset?q=')
        assert res.body.count('string_not_found_in_rest_of_template') == 2


class TestBulkActions(WsgiAppCase):

    @classmethod
    def setup_class(cls):
        search.clear()
        model.Session.add_all([
            model.User(name=u'sysadmin', apikey=u'sysadmin',
                       password=u'sysadmin', sysadmin=True),
        ])
        model.Session.commit()

        data_dict = '%s=1' % json.dumps({
            'name': 'org',
        })
        res = cls.app.post('/api/action/organization_create',
                            extra_environ={'Authorization': 'sysadmin'},
                            params=data_dict)
        cls.org_id = json.loads(res.body)['result']['id']

        cls.package_ids = []
        for i in range(0,12):
            data_dict = '%s=1' % json.dumps({
                'name': 'name{i}'.format(i=i),
                'owner_org': 'org',
            })
            res = cls.app.post('/api/action/package_create',
                                extra_environ={'Authorization': 'sysadmin'},
                                params=data_dict)
            cls.package_ids.append(json.loads(res.body)['result']['id'])


    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_01_make_private_then_public(self):
        data_dict = '%s=1' % json.dumps({
            'datasets': self.package_ids,
            'org_id': self.org_id,
        })
        res = self.app.post('/api/action/bulk_update_private',
                            extra_environ={'Authorization': 'sysadmin'},
                            params=data_dict)

        dataset_list = [row.private for row in
                        model.Session.query(model.Package.private).all()]
        assert len(dataset_list) == 12, len(dataset_list)
        assert all(dataset_list)

        res = self.app.get('/api/action/package_search?q=*:*')
        assert json.loads(res.body)['result']['count'] == 0

        res = self.app.post('/api/action/bulk_update_public',
                            extra_environ={'Authorization': 'sysadmin'},
                            params=data_dict)

        dataset_list = [row.private for row in
                        model.Session.query(model.Package.private).all()]
        assert len(dataset_list) == 12, len(dataset_list)
        assert not any(dataset_list)

        res = self.app.get('/api/action/package_search?q=*:*')
        assert json.loads(res.body)['result']['count'] == 12

    def test_02_bulk_delete(self):

        data_dict = '%s=1' % json.dumps({
            'datasets': self.package_ids,
            'org_id': self.org_id,
        })
        res = self.app.post('/api/action/bulk_update_delete',
                            extra_environ={'Authorization': 'sysadmin'},
                            params=data_dict)

        dataset_list = [row.state for row in
                        model.Session.query(model.Package.state).all()]
        assert len(dataset_list) == 12, len(dataset_list)
        assert all(state == 'deleted' for state in dataset_list)

        res = self.app.get('/api/action/package_search?q=*:*')
        assert json.loads(res.body)['result']['count'] == 0


class TestGroupOrgView(WsgiAppCase):

    @classmethod
    def setup_class(cls):
        model.Session.add_all([
            model.User(name=u'sysadmin', apikey=u'sysadmin',
                       password=u'sysadmin', sysadmin=True),
        ])
        model.Session.commit()

        org_dict = '%s=1' % json.dumps({
            'name': 'org',
        })
        res = cls.app.post('/api/action/organization_create',
                            extra_environ={'Authorization': 'sysadmin'},
                            params=org_dict)
        cls.org_id = json.loads(res.body)['result']['id']

        group_dict = '%s=1' % json.dumps({
            'name': 'group',
        })
        res = cls.app.post('/api/action/group_create',
                            extra_environ={'Authorization': 'sysadmin'},
                            params=group_dict)
        cls.group_id = json.loads(res.body)['result']['id']

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_1_view_org(self):
        res = self.app.get('/api/action/organization_show',
                params={'id': self.org_id})
        res_json = json.loads(res.body)
        assert res_json['success'] is True

        res = self.app.get('/api/action/group_show',
                params={'id': self.org_id}, expect_errors=True)
        res_json = json.loads(res.body)
        assert res_json['success'] is False

    def test_2_view_group(self):
        res = self.app.get('/api/action/group_show',
                params={'id': self.group_id})
        res_json = json.loads(res.body)
        assert res_json['success'] is True

        res = self.app.get('/api/action/organization_show',
                params={'id': self.group_id}, expect_errors=True)
        res_json = json.loads(res.body)
        assert res_json['success'] is False


class TestResourceAction(WsgiAppCase):

    sysadmin_user = None

    normal_user = None

    @classmethod
    def setup_class(cls):
        search.clear()
        CreateTestData.create()
        cls.sysadmin_user = model.User.get('testsysadmin')

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def _add_basic_package(self, package_name=u'test_package', **kwargs):
        package = {
            'name': package_name,
            'title': u'A Novel By Tolstoy',
            'resources': [{
                'description': u'Full text.',
                'format': u'plain text',
                'url': u'http://www.annakarenina.com/download/'
            }]
        }
        package.update(kwargs)

        postparams = '%s=1' % json.dumps(package)
        res = self.app.post('/api/action/package_create', params=postparams,
                            extra_environ={'Authorization': 'tester'})
        return json.loads(res.body)['result']

    def test_01_delete_resource(self):
        res_dict = self._add_basic_package()
        pkg_id = res_dict['id']

        resource_count = len(res_dict['resources'])
        id = res_dict['resources'][0]['id']
        url = '/api/action/resource_delete'

        # Use the sysadmin user because this package doesn't belong to an org
        res = self.app.post(url, params=json.dumps({'id': id}),
                extra_environ={'Authorization': str(self.sysadmin_user.apikey)})
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True

        url = '/api/action/package_show'
        res = self.app.get(url, {'id': pkg_id})
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True
        assert len(res_dict['result']['resources']) == resource_count - 1


class TestMember(WsgiAppCase):

    sysadmin = None

    group = None

    def setup(self):
        username = 'sysadmin'
        groupname = 'test group'
        organization_name = 'test organization'
        CreateTestData.create_user('sysadmin', **{ 'sysadmin': True })
        CreateTestData.create_groups([{ 'name': groupname },
                                      { 'name': organization_name,
                                        'type': 'organization'}])
        self.sysadmin = model.User.get(username)
        self.group = model.Group.get(groupname)

    def teardown(self):
        model.repo.rebuild_db()

    def test_group_member_create_works_user_id_and_group_id(self):
        self._assert_we_can_add_user_to_group(self.sysadmin.id, self.group.id)

    def test_group_member_create_works_with_user_id_and_group_name(self):
        self._assert_we_can_add_user_to_group(self.sysadmin.id, self.group.name)

    def test_group_member_create_works_with_user_name_and_group_name(self):
        self._assert_we_can_add_user_to_group(self.sysadmin.name, self.group.name)

    def _assert_we_can_add_user_to_group(self, user_id, group_id):
        user = model.User.get(user_id)
        group = model.Group.get(group_id)
        url = '/api/action/group_member_create'
        role = 'member'
        postparams = '%s=1' % json.dumps({
            'id': group_id,
            'username': user_id,
            'role': role})

        res = self.app.post(url, params=postparams,
                            extra_environ={'Authorization': str(user.apikey)})

        res = json.loads(res.body)
        groups = user.get_groups(group.type, role)
        group_ids = [g.id for g in groups]
        assert res['success'] is True, res
        assert group.id in group_ids, (group, user_groups)


class TestRelatedAction(WsgiAppCase):

    sysadmin_user = None

    normal_user = None

    @classmethod
    def setup_class(cls):
        search.clear()
        CreateTestData.create()
        cls.sysadmin_user = model.User.get('testsysadmin')

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def _add_basic_package(self, package_name=u'test_package', **kwargs):
        package = {
            'name': package_name,
            'title': u'A Novel By Tolstoy',
            'resources': [{
                'description': u'Full text.',
                'format': u'plain text',
                'url': u'http://www.annakarenina.com/download/'
            }]
        }
        package.update(kwargs)

        postparams = '%s=1' % json.dumps(package)
        res = self.app.post('/api/action/package_create', params=postparams,
                            extra_environ={'Authorization': 'tester'})
        return json.loads(res.body)['result']

    def test_update_add_related_item(self):
        package = self._add_basic_package()
        related_item = {
            "description": "Testing a Description",
            "url": "http://example.com/image.png",
            "title": "Testing",
            "featured": 0,
            "image_url": "http://example.com/image.png",
            "type": "idea",
            "dataset_id": package['id'],
        }
        related_item_json = json.dumps(related_item)
        res_create = self.app.post('/api/action/related_create',
                                   params=related_item_json,
                                   extra_environ={'Authorization': 'tester'})
        assert res_create.json['success']

        related_update = res_create.json['result']
        related_update = {'id': related_update['id'], 'title': 'Updated'}
        related_update_json = json.dumps(related_update)
        res_update = self.app.post('/api/action/related_update',
                                   params=related_update_json,
                                   extra_environ={'Authorization': 'tester'})
        assert res_update.json['success']
        res_update_json = res_update.json['result']
        assert res_update_json['title'] == related_update['title']

        related_item.pop('title')
        related_item.pop('dataset_id')
        for field in related_item:
            assert related_item[field] == res_update_json[field]
