# encoding: utf-8

import json
from nose.tools import assert_equal
import ckan.lib.search as search

import ckan.model as model
from ckan.lib.create_test_data import CreateTestData
from ckan.tests.legacy import WsgiAppCase
from ckan.tests.legacy import StatusCodes

class TestAction(WsgiAppCase):
    @classmethod
    def setup_class(cls):
        search.clear_all()
        CreateTestData.create()
        cls.sysadmin_user = model.User.get('testsysadmin')
        cls.normal_user = model.User.get('annafan')
        CreateTestData.make_some_vocab_tags()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_08_user_create_not_authorized(self):
        postparams = '%s=1' % json.dumps({'name':'test_create_from_action_api', 'password':'testpass'})
        res = self.app.post('/api/action/user_create', params=postparams,
                            status=StatusCodes.STATUS_403_ACCESS_DENIED)
        res_obj = json.loads(res.body)
        assert '/api/3/action/help_show?name=user_create' in res_obj['help']
        assert res_obj['success'] is False
        assert res_obj['error']['__type'] == 'Authorization Error'

    def test_09_user_create(self):
        user_dict = {'name':'test_create_from_action_api',
                      'about': 'Just a test user',
                      'email': 'me@test.org',
                      'password':'testpass'}

        postparams = '%s=1' % json.dumps(user_dict)
        res = self.app.post('/api/action/user_create', params=postparams,
                            extra_environ={'Authorization': str(self.sysadmin_user.apikey)})
        res_obj = json.loads(res.body)
        assert '/api/3/action/help_show?name=user_create' in res_obj['help']
        assert res_obj['success'] == True
        result = res_obj['result']
        assert result['name'] == user_dict['name']
        assert result['about'] == user_dict['about']
        assert 'apikey' in result
        assert 'created' in result
        assert 'display_name' in result
        assert 'number_created_packages' in result
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
        assert '/api/3/action/help_show?name=tag_autocomplete' in res_obj['help']

        #Normal query
        postparams = '%s=1' % json.dumps({'q':'r'})
        res = self.app.post('/api/action/tag_autocomplete', params=postparams)
        res_obj = json.loads(res.body)
        assert res_obj['success'] == True
        assert res_obj['result'] == ['russian', 'tolerance']
        assert '/api/3/action/help_show?name=tag_autocomplete' in res_obj['help']

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
