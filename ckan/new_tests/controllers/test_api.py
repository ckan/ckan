'''
NB Don't test logic functions here. This is just for the mechanics of the API
controller itself.
'''
import json

import ckan.new_tests.helpers as helpers


class TestApiController(helpers.FunctionalTestBase):

    def test_unicode_in_error_message_works_ok(self):
        # Use tag_delete to echo back some unicode
        app = self._get_test_app()
        org_url = '/api/action/tag_delete'
        data_dict = {'id': u'Delta symbol: \u0394'}  # unicode gets rec'd ok
        postparams = '%s=1' % json.dumps(data_dict)
        response = app.post(url=org_url, params=postparams, status=404)
        # The unicode is backslash encoded (because that is the default when
        # you do str(exception) )
        assert 'Delta symbol: \\u0394' in response.body
