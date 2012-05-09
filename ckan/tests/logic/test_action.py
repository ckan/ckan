import re
import json
from pprint import pprint
from nose.tools import assert_equal, assert_raises
from nose.plugins.skip import SkipTest
from pylons import config

import ckan
from ckan.lib.create_test_data import CreateTestData
from ckan.lib.dictization.model_dictize import resource_dictize
import ckan.model as model
from ckan.tests import WsgiAppCase
from ckan.tests.functional.api import assert_dicts_equal_ignoring_ordering
from ckan.tests import setup_test_search_index, search_related
from ckan.logic import get_action, NotAuthorized
from ckan.logic.action import get_domain_object

from ckan import plugins
from ckan.plugins import SingletonPlugin, implements, IPackageController


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
    def setup_class(cls):
        CreateTestData.create()
        cls.sysadmin_user = model.User.get('testsysadmin')
        cls.normal_user = model.User.get('annafan')
        cls.make_some_vocab_tags()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    @classmethod
    def make_some_vocab_tags(cls):
        model.repo.new_revision()

        # Create a couple of vocabularies.
        genre_vocab = model.Vocabulary(u'genre')
        model.Session.add(genre_vocab)
        composers_vocab = model.Vocabulary(u'composers')
        model.Session.add(composers_vocab)

        # Create some additional free tags for tag search tests.
        tolkien_tag = model.Tag(name="tolkien")
        model.Session.add(tolkien_tag)
        toledo_tag = model.Tag(name="toledo")
        model.Session.add(toledo_tag)
        tolerance_tag = model.Tag(name="tolerance")
        model.Session.add(tolerance_tag)
        tollbooth_tag = model.Tag(name="tollbooth")
        model.Session.add(tollbooth_tag)
        # We have to add free tags to a package or they won't show up in tag results.
        model.Package.get('warandpeace').add_tags((tolkien_tag, toledo_tag,
            tolerance_tag, tollbooth_tag))

        # Create some tags that belong to vocabularies.
        sonata_tag = model.Tag(name=u'sonata', vocabulary_id=genre_vocab.id)
        model.Session.add(sonata_tag)

        bach_tag = model.Tag(name=u'Bach', vocabulary_id=composers_vocab.id)
        model.Session.add(bach_tag)

        neoclassical_tag = model.Tag(name='neoclassical',
                vocabulary_id=genre_vocab.id)
        model.Session.add(neoclassical_tag)

        neofolk_tag = model.Tag(name='neofolk', vocabulary_id=genre_vocab.id)
        model.Session.add(neofolk_tag)

        neomedieval_tag = model.Tag(name='neomedieval',
                vocabulary_id=genre_vocab.id)
        model.Session.add(neomedieval_tag)

        neoprog_tag = model.Tag(name='neoprog',
                vocabulary_id=genre_vocab.id)
        model.Session.add(neoprog_tag)

        neopsychedelia_tag = model.Tag(name='neopsychedelia',
                vocabulary_id=genre_vocab.id)
        model.Session.add(neopsychedelia_tag)

        neosoul_tag = model.Tag(name='neosoul', vocabulary_id=genre_vocab.id)
        model.Session.add(neosoul_tag)

        nerdcore_tag = model.Tag(name='nerdcore', vocabulary_id=genre_vocab.id)
        model.Session.add(nerdcore_tag)

        model.Package.get('warandpeace').add_tag(bach_tag)
        model.Package.get('annakarenina').add_tag(sonata_tag)

        model.Session.commit()

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

    def test_02_package_autocomplete_match_name(self):
        postparams = '%s=1' % json.dumps({'q':'war'})
        res = self.app.post('/api/action/package_autocomplete', params=postparams)
        res_obj = json.loads(res.body)
        assert_equal(res_obj['success'], True)
        pprint(res_obj['result'][0]['name'])
        assert_equal(res_obj['result'][0]['name'], 'warandpeace')
        assert_equal(res_obj['result'][0]['title'], 'A Wonderful Story')
        assert_equal(res_obj['result'][0]['match_field'], 'name')
        assert_equal(res_obj['result'][0]['match_displayed'], 'warandpeace')

    def test_02_package_autocomplete_match_title(self):
        postparams = '%s=1' % json.dumps({'q':'a%20w'})
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
        package_updated.pop('metadata_created')
        package_updated.pop('metadata_modified')

        package_created.pop('revision_id')
        package_created.pop('revision_timestamp')
        package_created.pop('metadata_created')
        package_created.pop('metadata_modified')
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

    def test_06a_tag_list(self):
        postparams = '%s=1' % json.dumps({})
        res = self.app.post('/api/action/tag_list', params=postparams)
        resbody = json.loads(res.body)
        assert resbody['success'] is True
        assert sorted(resbody['result']) == sorted(['russian', 'tolstoy',
                u'Flexible \u30a1', 'tollbooth', 'tolkien', 'toledo',
                'tolerance'])
        assert resbody['help'].startswith(
                'Return a list of tag dictionaries.')
        #Get all fields
        postparams = '%s=1' % json.dumps({'all_fields':True})
        res = self.app.post('/api/action/tag_list', params=postparams)
        res_obj = json.loads(res.body)
        pprint(res_obj)
        assert res_obj['success'] == True

        names = [ res_obj['result'][i]['name'] for i in xrange(len(res_obj['result'])) ]
        russian_index = names.index('russian')
        tolstoy_index = names.index('tolstoy')
        flexible_index = names.index(u'Flexible \u30a1')

        assert res_obj['result'][russian_index]['name'] == 'russian'
        assert res_obj['result'][tolstoy_index]['name'] == 'tolstoy'

        # The "moo" package may part of the retrieved packages, depending
        # upon whether this test is run in isolation from the rest of the
        # test suite or not.
        number_of_russian_packages = len(res_obj['result'][russian_index]['packages'])   # warandpeace, annakarenina (moo?)
        number_of_tolstoy_packages = len(res_obj['result'][tolstoy_index]['packages'])   # annakarenina
        number_of_flexible_packages = len(res_obj['result'][flexible_index]['packages']) # warandpeace, annakarenina (moo?)

        # Assert we have the correct number of packages, independantly of
        # whether the "moo" package may exist or not.
        assert number_of_russian_packages - number_of_tolstoy_packages == 1
        assert number_of_flexible_packages == (number_of_russian_packages - number_of_tolstoy_packages) + 1

        assert 'id' in res_obj['result'][0]
        assert 'id' in res_obj['result'][1]
        assert 'id' in res_obj['result'][2]

    def test_06b_tag_list_vocab(self):
        vocab_name = 'test-vocab'
        tag_name = 'test-vocab-tag'

        # create vocab
        params = json.dumps({'name': vocab_name})
        extra_environ = {'Authorization' : str(self.sysadmin_user.apikey)}
        response = self.app.post('/api/action/vocabulary_create', params=params,
                                 extra_environ=extra_environ)
        assert response.json['success']
        vocab_id = response.json['result']['id']

        # create new tag with vocab
        params = json.dumps({'name': tag_name, 'vocabulary_id': vocab_id})
        extra_environ = {'Authorization' : str(self.sysadmin_user.apikey)}
        response = self.app.post('/api/action/tag_create', params=params,
                                 extra_environ=extra_environ)
        assert response.json['success'] == True

        # check that tag shows up in list
        params = '%s=1' % json.dumps({'vocabulary_id': vocab_name})
        res = self.app.post('/api/action/tag_list', params=params)
        body = json.loads(res.body)
        assert body['success'] is True
        assert body['result'] == [tag_name]
        assert body['help'].startswith('Return a list of tag dictionaries.')

        # check that invalid vocab name results in a 404
        params = '%s=1' % json.dumps({'vocabulary_id': 'invalid-vocab-name'})
        res = self.app.post('/api/action/tag_list', params=params, status=404)

    def test_07_tag_show(self):
        postparams = '%s=1' % json.dumps({'id':'russian'})
        res = self.app.post('/api/action/tag_show', params=postparams)
        res_obj = json.loads(res.body)
        assert res_obj['help'] == 'Shows tag details'
        assert res_obj['success'] == True
        result = res_obj['result']
        assert result['name'] == 'russian'
        assert 'id' in result
        assert 'packages' in result

        packages = [package['name'] for package in result['packages']]

        # the "moo" package may be part of the retrieved packages, depending
        # upon whether or not this test is run in isolation from the other tests
        # in the suite.
        expected_packages = ['annakarenina', 'warandpeace'] + (
            ['moo'] if 'moo' in packages else [])

        assert sorted(packages) == sorted(expected_packages), "%s != %s" %(packages, expected_packages)

    def test_07_flexible_tag_show(self):
        """
        Asserts that the api can be used to retrieve the details of the flexible tag.

        The flexible tag is the tag with spaces, punctuation and foreign
        characters in its name, that's created in `ckan/lib/create_test_data.py`.
        """
        postparams = '%s=1' % json.dumps({'id':u'Flexible \u30a1'})
        res = self.app.post('/api/action/tag_show', params=postparams)
        res_obj = json.loads(res.body)
        assert res_obj['help'] == 'Shows tag details'
        assert res_obj['success'] == True
        result = res_obj['result']
        assert result['name'] == u'Flexible \u30a1'
        assert 'id' in result
        assert 'packages' in result and len(result['packages']) == 2

        assert sorted([package['name'] for package in result['packages']]) == \
               sorted(['annakarenina', 'warandpeace'])

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
                                status=self.STATUS_409_CONFLICT)
            res_obj = json.loads(res.body)
            for expected_message in test_call['messages']:
                assert expected_message[1] in ''.join(res_obj['error'][expected_message[0]])

    def test_13_group_list(self):
        postparams = '%s=1' % json.dumps({})
        res = self.app.post('/api/action/group_list', params=postparams)
        res_obj = json.loads(res.body)
        assert_dicts_equal_ignoring_ordering(
            res_obj,
            {
                'result': [
                    'david',
                    'roger',
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

    def test_15a_tag_search_with_empty_query(self):
        for q in ('missing', None, '', '  '):
            paramd = {}
            if q != 'missing':
                paramd['q'] = q
            params = json.dumps(paramd)
            res = self.app.post('/api/action/tag_search', params=params)
            assert res.json['success'] is True
            assert res.json['result']['count'] == 0
            assert res.json['result']['results'] == []

    def test_15a_tag_search_with_no_matches(self):
        paramd = {'q': 'no matches' }
        params = json.dumps(paramd)
        res = self.app.post('/api/action/tag_search', params=params)
        assert res.json['success'] is True
        assert res.json['result']['count'] == 0
        assert res.json['result']['results'] == []

    def test_15a_tag_search_with_one_match(self):
        paramd = {'q': 'russ' }
        params = json.dumps(paramd)
        res = self.app.post('/api/action/tag_search', params=params)
        assert res.json['success'] is True
        assert res.json['result']['count'] == 1
        tag_dicts = res.json['result']['results']
        assert len(tag_dicts) == 1
        assert tag_dicts[0]['name'] == 'russian'

    def test_15a_tag_search_with_many_matches(self):
        paramd = {'q': 'tol' }
        params = json.dumps(paramd)
        res = self.app.post('/api/action/tag_search', params=params)
        assert res.json['success'] is True
        assert res.json['result']['count'] == 5
        tag_dicts = res.json['result']['results']
        assert ([tag['name'] for tag in tag_dicts] ==
                sorted(['tolkien', 'toledo', 'tolerance', 'tollbooth', 'tolstoy']))

    def test_15a_tag_search_with_vocab_and_empty_query(self):
        for q in ('missing', None, '', '  '):
            paramd = {'vocabulary_id': 'genre'}
            if q != 'missing':
                paramd['q'] = q
            params = json.dumps(paramd)
            res = self.app.post('/api/action/tag_search', params=params)
            assert res.json['success'] is True
            assert res.json['result']['count'] == 0
            assert res.json['result']['results'] == []

    def test_15a_tag_search_with_vocab_and_one_match(self):
        paramd = {'q': 'son', 'vocabulary_id': 'genre' }
        params = json.dumps(paramd)
        res = self.app.post('/api/action/tag_search', params=params)
        assert res.json['success'] is True
        assert res.json['result']['count'] == 1
        tag_dicts = res.json['result']['results']
        assert len(tag_dicts) == 1
        assert tag_dicts[0]['name'] == 'sonata'

    def test_15a_tag_search_with_vocab_and_multiple_matches(self):
        paramd = {'q': 'neo', 'vocabulary_id': 'genre' }
        params = json.dumps(paramd)
        res = self.app.post('/api/action/tag_search', params=params)
        assert res.json['success'] is True
        assert res.json['result']['count'] == 6
        tag_dicts = res.json['result']['results']
        assert [tag['name'] for tag in tag_dicts] == sorted(('neoclassical',
            'neofolk', 'neomedieval', 'neoprog', 'neopsychedelia', 'neosoul'))

    def test_15a_tag_search_with_vocab_and_no_matches(self):
        paramd = {'q': 'xxxxxxx', 'vocabulary_id': 'genre' }
        params = json.dumps(paramd)
        res = self.app.post('/api/action/tag_search', params=params)
        assert res.json['success'] is True
        assert res.json['result']['count'] == 0
        tag_dicts = res.json['result']['results']
        assert tag_dicts == []

    def test_15a_tag_search_with_vocab_that_does_not_exist(self):
        paramd = {'q': 'neo', 'vocabulary_id': 'xxxxxx' }
        params = json.dumps(paramd)
        self.app.post('/api/action/tag_search', params=params, status=404)

    def test_15a_tag_search_with_invalid_vocab(self):
        for vocab_name in (None, '', 'a', 'e'*200):
            paramd = {'q': 'neo', 'vocabulary_id': vocab_name }
            params = json.dumps(paramd)
            self.app.post('/api/action/tag_search', params=params, status=404)

    def test_15_tag_autocomplete(self):
        #Empty query
        postparams = '%s=1' % json.dumps({})
        res = self.app.post('/api/action/tag_autocomplete', params=postparams)
        res_obj = json.loads(res.body)
        assert res_obj['success'] == True
        assert res_obj['result'] == []
        assert res_obj['help'].startswith(
                'Return a list of tag names that contain the given string.')

        #Normal query
        postparams = '%s=1' % json.dumps({'q':'r'})
        res = self.app.post('/api/action/tag_autocomplete', params=postparams)
        res_obj = json.loads(res.body)
        assert res_obj['success'] == True
        assert res_obj['result'] == ['russian', 'tolerance']
        assert res_obj['help'].startswith(
                'Return a list of tag names that contain the given string.')

    def test_15_tag_autocomplete_tag_with_spaces(self):
        """Asserts autocomplete finds tags that contain spaces"""

        CreateTestData.create_arbitrary([{
            'name': u'package-with-tag-that-has-a-space-1',
            'tags': [u'with space'],
            'license': 'never_heard_of_it',
            }])

        postparams = '%s=1' % json.dumps({'q':'w'})
        res = self.app.post('/api/action/tag_autocomplete', params=postparams)
        res_obj = json.loads(res.body)
        assert res_obj['success']
        assert 'with space' in res_obj['result'], res_obj['result']

    def test_15_tag_autocomplete_tag_with_foreign_characters(self):
        """Asserts autocomplete finds tags that contain foreign characters"""

        CreateTestData.create_arbitrary([{
            'name': u'package-with-tag-that-has-a-foreign-character-1',
            'tags': [u'greek beta \u03b2'],
            'license': 'never_heard_of_it',
            }])

        postparams = '%s=1' % json.dumps({'q':'greek'})
        res = self.app.post('/api/action/tag_autocomplete', params=postparams)
        res_obj = json.loads(res.body)
        assert res_obj['success']
        assert u'greek beta \u03b2' in res_obj['result'], res_obj['result']

    def test_15_tag_autocomplete_tag_with_punctuation(self):
        """Asserts autocomplete finds tags that contain punctuation"""

        CreateTestData.create_arbitrary([{
            'name': u'package-with-tag-that-has-a-fullstop-1',
            'tags': [u'fullstop.'],
            'license': 'never_heard_of_it',
            }])

        postparams = '%s=1' % json.dumps({'q':'fullstop'})
        res = self.app.post('/api/action/tag_autocomplete', params=postparams)
        res_obj = json.loads(res.body)
        assert res_obj['success']
        assert u'fullstop.' in res_obj['result'], res_obj['result']

    def test_15_tag_autocomplete_tag_with_capital_letters(self):
        """
        Asserts autocomplete finds tags that contain capital letters
        """

        CreateTestData.create_arbitrary([{
            'name': u'package-with-tag-that-has-a-capital-letter-1',
            'tags': [u'CAPITAL idea old chap'],
            'license': 'never_heard_of_it',
            }])

        postparams = '%s=1' % json.dumps({'q':'idea'})
        res = self.app.post('/api/action/tag_autocomplete', params=postparams)
        res_obj = json.loads(res.body)
        assert res_obj['success']
        assert u'CAPITAL idea old chap' in res_obj['result'], res_obj['result']

    def test_15_tag_autocomplete_search_with_space(self):
        """
        Asserts that a search term containing a space works correctly
        """

        CreateTestData.create_arbitrary([{
            'name': u'package-with-tag-that-has-a-space-2',
            'tags': [u'with space'],
            'license': 'never_heard_of_it',
            }])

        postparams = '%s=1' % json.dumps({'q':'th sp'})
        res = self.app.post('/api/action/tag_autocomplete', params=postparams)
        res_obj = json.loads(res.body)
        assert res_obj['success']
        assert 'with space' in res_obj['result'], res_obj['result']

    def test_15_tag_autocomplete_search_with_foreign_character(self):
        """
        Asserts that a search term containing a foreign character works correctly
        """

        CreateTestData.create_arbitrary([{
            'name': u'package-with-tag-that-has-a-foreign-character-2',
            'tags': [u'greek beta \u03b2'],
            'license': 'never_heard_of_it',
            }])

        postparams = '%s=1' % json.dumps({'q':u'\u03b2'})
        res = self.app.post('/api/action/tag_autocomplete', params=postparams)
        res_obj = json.loads(res.body)
        assert res_obj['success']
        assert u'greek beta \u03b2' in res_obj['result'], res_obj['result']

    def test_15_tag_autocomplete_search_with_punctuation(self):
        """
        Asserts that a search term containing punctuation works correctly
        """

        CreateTestData.create_arbitrary([{
            'name': u'package-with-tag-that-has-a-fullstop-2',
            'tags': [u'fullstop.'],
            'license': 'never_heard_of_it',
            }])

        postparams = '%s=1' % json.dumps({'q':u'stop.'})
        res = self.app.post('/api/action/tag_autocomplete', params=postparams)
        res_obj = json.loads(res.body)
        assert res_obj['success']
        assert 'fullstop.' in res_obj['result'], res_obj['result']

    def test_15_tag_autocomplete_search_with_capital_letters(self):
        """
        Asserts that a search term containing capital letters works correctly
        """

        CreateTestData.create_arbitrary([{
            'name': u'package-with-tag-that-has-a-capital-letter-2',
            'tags': [u'CAPITAL idea old chap'],
            'license': 'never_heard_of_it',
            }])

        postparams = '%s=1' % json.dumps({'q':u'CAPITAL'})
        res = self.app.post('/api/action/tag_autocomplete', params=postparams)
        res_obj = json.loads(res.body)
        assert res_obj['success']
        assert 'CAPITAL idea old chap' in res_obj['result'], res_obj['result']

    def test_15_tag_autocomplete_is_case_insensitive(self):
        CreateTestData.create_arbitrary([{
            'name': u'package-with-tag-that-has-a-capital-letter-3',
            'tags': [u'MIX of CAPITALS and LOWER case'],
            'license': 'never_heard_of_it',
            }])

        postparams = '%s=1' % json.dumps({'q':u'lower case'})
        res = self.app.post('/api/action/tag_autocomplete', params=postparams)
        res_obj = json.loads(res.body)
        assert res_obj['success']
        assert 'MIX of CAPITALS and LOWER case' in res_obj['result'], res_obj['result']

    def test_15_tag_autocomplete_with_vocab_and_empty_query(self):
        for q in ('missing', None, '', '  '):
            paramd = {'vocabulary_id': u'genre'}
            if q != 'missing':
                paramd['q'] = q
            params = json.dumps(paramd)
            res = self.app.post('/api/action/tag_autocomplete', params=params)
            assert res.json['success'] is True
            assert res.json['result'] == []

    def test_15_tag_autocomplete_with_vocab_and_single_match(self):
        paramd = {'vocabulary_id': u'genre', 'q': 'son'}
        params = json.dumps(paramd)
        res = self.app.post('/api/action/tag_autocomplete', params=params)
        assert res.json['success'] is True
        assert res.json['result'] == ['sonata'], res.json['result']

    def test_15_tag_autocomplete_with_vocab_and_multiple_matches(self):
        paramd = {'vocabulary_id': 'genre', 'q': 'neo'}
        params = json.dumps(paramd)
        res = self.app.post('/api/action/tag_autocomplete', params=params)
        assert res.json['success'] is True
        assert res.json['result'] == sorted(('neoclassical', 'neofolk',
            'neomedieval', 'neoprog', 'neopsychedelia', 'neosoul'))

    def test_15_tag_autocomplete_with_vocab_and_no_matches(self):
        paramd = {'vocabulary_id': 'composers', 'q': 'Jonny Greenwood'}
        params = json.dumps(paramd)
        res = self.app.post('/api/action/tag_autocomplete', params=params)
        assert res.json['success'] is True
        assert res.json['result'] == []

    def test_15_tag_autocomplete_with_vocab_that_does_not_exist(self):
        for q in ('', 'neo'):
            paramd = {'vocabulary_id': 'does_not_exist', 'q': q}
            params = json.dumps(paramd)
            res = self.app.post('/api/action/tag_autocomplete', params=params,
                    status=404)
            assert res.json['success'] is False

    def test_15_tag_autocomplete_with_invalid_vocab(self):
        for vocab_name in (None, '', 'a', 'e'*200):
            for q in (None, '', 'son'):
                paramd = {'vocabulary_id': vocab_name, 'q': q}
                params = json.dumps(paramd)
                res = self.app.post('/api/action/tag_autocomplete', params=params,
                        status=404)
                assert res.json['success'] is False

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
        resource_created.pop('url')
        resource_created.pop('revision_id')
        resource_created.pop('revision_timestamp')
        assert resource_updated == resource_created

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
            status=self.STATUS_403_ACCESS_DENIED
        )
        res_obj = json.loads(res.body)
        expected_res_obj = {
            'help': None,
            'success': False,
            'error': {'message': 'Access denied', '__type': 'Authorization Error'}
        }
        assert res_obj == expected_res_obj, res_obj

    def test_23_task_status_validation(self):
        task_status = {}
        postparams = '%s=1' % json.dumps(task_status)
        res = self.app.post(
            '/api/action/task_status_update', params=postparams,
            extra_environ={'Authorization': str(self.sysadmin_user.apikey)},
            status=self.STATUS_409_CONFLICT
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
        resource_dict = resource_dictize(resource, {'model': model})
        result.pop('revision_timestamp')
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
        context = {'model': model, 'session': model.Session, 'user': self.sysadmin_user.name, 'api_version': 2}
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
        assert len(group_packages) == 2, group_packages
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
        assert 'Request data JSON decoded to u\'not a dict\' but it needs to be a dictionary.' in res.body, res.body

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

    def test_34_roles_show_for_authgroup_on_authgroup(self):
        anna = model.Package.by_name(u'annakarenina')
        annafan = model.User.by_name(u'annafan')
        authgroup = model.AuthorizationGroup.by_name(u'anauthzgroup')
        authgroup2 = model.AuthorizationGroup.by_name(u'anotherauthzgroup')
        
        model.add_authorization_group_to_role(authgroup2, 'editor', authgroup)
        model.repo.commit_and_remove()
        
        postparams = '%s=1' % json.dumps({'domain_object': authgroup.id,
                                          'authorization_group': authgroup2.id})
        res = self.app.post('/api/action/roles_show', params=postparams,
                            extra_environ={'Authorization': str(annafan.apikey)},
                            status=200)
        
        authgroup_roles = self.get_roles(authgroup.id, authgroup_ref=authgroup2.name)
        assert_equal(authgroup_roles, ['"anotherauthzgroup" is "editor" on "anauthzgroup"'])

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

    def get_roles(self, domain_object_ref, user_ref=None, authgroup_ref=None,
                  prettify=True):
        data_dict = {'domain_object': domain_object_ref}
        if user_ref:
            data_dict['user'] = user_ref
        if authgroup_ref:
            data_dict['authorization_group'] = authgroup_ref
        role_dicts = get_action('roles_show') \
                     ({'model': model, 'session': model.Session}, \
                      data_dict)['roles']
        if prettify:
            role_dicts = self.prettify_role_dicts(role_dicts)
        return role_dicts

    def prettify_role_dicts(self, role_dicts, one_per_line=True):
        '''Replace ids with names'''
        pretty_roles = []
        for role_dict in role_dicts:
            pretty_role = {}
            for key, value in role_dict.items():
                if key.endswith('_id') and value and key != 'user_object_role_id':
                    pretty_key = key[:key.find('_id')]
                    domain_object = get_domain_object(model, value)
                    pretty_value = domain_object.name
                    pretty_role[pretty_key] = pretty_value
                else:
                    pretty_role[key] = value
            if one_per_line:
                pretty_role = '"%s" is "%s" on "%s"' % (
                    pretty_role.get('user') or pretty_role.get('authorized_group'),
                    pretty_role['role'],
                    pretty_role.get('package') or pretty_role.get('group') or pretty_role.get('authorization_group'))
            pretty_roles.append(pretty_role)
        return pretty_roles

    def test_36_user_role_update_for_auth_group(self):
        anna = model.Package.by_name(u'annakarenina')
        annafan = model.User.by_name(u'annafan')
        authgroup = model.AuthorizationGroup.by_name(u'anauthzgroup')
        all_roles_before = self.get_roles(anna.id)
        authgroup_roles_before = self.get_roles(anna.id, authgroup_ref=authgroup.name)
        assert_equal(len(authgroup_roles_before), 0)
        postparams = '%s=1' % json.dumps({'authorization_group': authgroup.name,
                                          'domain_object': anna.id,
                                          'roles': ['editor']})

        res = self.app.post('/api/action/user_role_update', params=postparams,
                            extra_environ={'Authorization': str(annafan.apikey)},
                            status=200)

        results = json.loads(res.body)['result']
        assert_equal(len(results['roles']), 1)
        anna = model.Package.by_name(u'annakarenina')
        authgroup = model.AuthorizationGroup.by_name(u'anauthzgroup')

        assert_equal(results['roles'][0]['role'], 'editor')
        assert_equal(results['roles'][0]['package_id'], anna.id)
        assert_equal(results['roles'][0]['authorized_group_id'], authgroup.id)
        
        all_roles_after = self.get_roles(anna.id)
        authgroup_roles_after = self.get_roles(anna.id, authgroup_ref=authgroup.name)
        assert_equal(set(all_roles_before) ^ set(all_roles_after),
                     set([u'"anauthzgroup" is "editor" on "annakarenina"']))
        
        roles_after = get_action('roles_show') \
                      ({'model': model, 'session': model.Session}, \
                       {'domain_object': anna.id,
                        'authorization_group': authgroup.name})
        assert_equal(results['roles'], roles_after['roles'])

    def test_37_user_role_update_disallowed(self):
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
        all_roles_before = self.get_roles(anna.id)
        user_roles_before = self.get_roles(anna.id, user_ref=annafan.name)
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
        all_roles_after = self.get_roles(anna.id)
        user_roles_after = self.get_roles(anna.id, user_ref=annafan.name)
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
        res = self.app.post('/api/action/resource_status_show', 
                            params=json.dumps({'id': '749cdcf2-3fc8-44ae-aed0-5eff8cc5032c'}),
                            status=200)

        assert json.loads(res.body) == {"help": None, "success": True, "result": [{"status": "FAILURE", "entity_id": "749cdcf2-3fc8-44ae-aed0-5eff8cc5032c", "task_type": "qa", "last_updated": "2012-04-20T21:32:45.553986", "date_done": "2012-04-20T21:33:01.622557", "entity_type": "resource", "traceback": "Traceback", "value": "51f2105d-85b1-4393-b821-ac11475919d9", "state": None, "key": "celery_task_id", "error": "", "id": "5753adae-cd0d-4327-915d-edd832d1c9a3"}]}


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
    def setup_class(self):
        setup_test_search_index()
        CreateTestData.create()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_1_basic(self):
        postparams = '%s=1' % json.dumps({
                'q':'tolstoy',
                'facet.field': ('groups', 'tags', 'res_format', 'license'),
                'rows': 20,
                'start': 0,
            })
        res = self.app.post('/api/action/package_search', params=postparams)
        res = json.loads(res.body)
        result = res['result']
        assert_equal(res['success'], True)
        assert_equal(result['count'], 1)
        assert_equal(result['results'][0]['name'], 'annakarenina')

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
        assert '"Invalid search parameters: [u\'weird_param\']' in res.body, res.body

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
        model.repo.commit_and_remove()

        res = self.app.post('/api/action/package_search', params=search_params)
        result = json.loads(res.body)['result']
        result_names = [r['name'] for r in result['results']]
        assert result_names == ['warandpeace', 'annakarenina'], result_names

        # modify annakarenina, check that it is the first search result
        rev = model.repo.new_revision()
        pkg = model.Package.get('annakarenina')
        pkg.title = "A Novel By Tolstoy [UPDATED]"
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
                            extra_environ={'Authorization': 'tester'})

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
        assert 'facets' in search_results

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
        

