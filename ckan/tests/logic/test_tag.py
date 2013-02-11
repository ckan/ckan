import json
from pprint import pprint
from nose.tools import assert_equal, assert_raises
import ckan.lib.search as search

import ckan.model as model
from ckan.lib.create_test_data import CreateTestData
from ckan.tests import WsgiAppCase
from ckan.tests import StatusCodes

class TestAction(WsgiAppCase):
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

    def test_06a_tag_list(self):
        postparams = '%s=1' % json.dumps({})
        res = self.app.post('/api/action/tag_list', params=postparams)
        resbody = json.loads(res.body)
        assert resbody['success'] is True
        assert sorted(resbody['result']) == sorted(['russian', 'tolstoy',
                u'Flexible \u30a1', 'tollbooth', 'tolkien', 'toledo',
                'tolerance'])
        assert resbody['help'].startswith(
                "Return a list of the site's tags.")
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
        assert body['help'].startswith("Return a list of the site's tags.")

        # check that invalid vocab name results in a 404
        params = '%s=1' % json.dumps({'vocabulary_id': 'invalid-vocab-name'})
        res = self.app.post('/api/action/tag_list', params=params, status=404)

    def test_07_tag_show(self):
        postparams = '%s=1' % json.dumps({'id':'russian'})
        res = self.app.post('/api/action/tag_show', params=postparams)
        res_obj = json.loads(res.body)
        assert res_obj['help'].startswith(
                "Return the details of a tag and all its datasets.")
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
        assert res_obj['help'].startswith(
                "Return the details of a tag and all its datasets.")
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
                            status=StatusCodes.STATUS_403_ACCESS_DENIED)
        res_obj = json.loads(res.body)
        assert res_obj['help'].startswith("Create a new user.")
        assert res_obj['success'] is False
        assert res_obj['error'] == {'message': 'Access denied', '__type': 'Authorization Error'}

    def test_09_user_create(self):
        user_dict = {'name':'test_create_from_action_api',
                      'about': 'Just a test user',
                      'email': 'me@test.org',
                      'password':'testpass'}

        postparams = '%s=1' % json.dumps(user_dict)
        res = self.app.post('/api/action/user_create', params=postparams,
                            extra_environ={'Authorization': str(self.sysadmin_user.apikey)})
        res_obj = json.loads(res.body)
        assert res_obj['help'].startswith("Create a new user.")
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

    def test_15a_tag_search_with_one_match_using_fields_parameter(self):
        paramd = {'fields': {'tags': 'russ'} }
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

    def test_15a_tag_search_with_many_matches_paged(self):
        paramd = {'q': 'tol', 'limit': 2, 'offset': 2 }
        params = json.dumps(paramd)
        res = self.app.post('/api/action/tag_search', params=params)
        assert res.json['success'] is True
        assert res.json['result']['count'] == 5
        tag_dicts = res.json['result']['results']
        assert_equal ([tag['name'] for tag in tag_dicts],
                      [u'tolkien', u'tollbooth'])

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
                "Return a list of tag names that contain a given string.")

        #Normal query
        postparams = '%s=1' % json.dumps({'q':'r'})
        res = self.app.post('/api/action/tag_autocomplete', params=postparams)
        res_obj = json.loads(res.body)
        assert res_obj['success'] == True
        assert res_obj['result'] == ['russian', 'tolerance']
        assert res_obj['help'].startswith(
                'Return a list of tag names that contain a given string.')

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
