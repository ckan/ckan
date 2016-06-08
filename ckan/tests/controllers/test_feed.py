# encoding: utf-8


from ckan.lib.helpers import url_for

import ckan.tests.helpers as helpers
import ckan.tests.factories as factories


class TestFeedNew(helpers.FunctionalTestBase):

    def test_atom_feed_page_zero_gives_error(self):
        group = factories.Group()

        app = self._get_test_app()
        with app.flask_app.test_request_context():
            offset = url_for(controller='feed', action='group',
                             id=group['name']) + '?page=0'
        res = app.get(offset, status=400)
        assert '"page" parameter must be a positive integer' in res, res

    def test_atom_feed_page_negative_gives_error(self):
        group = factories.Group()

        app = self._get_test_app()
        with app.flask_app.test_request_context():
            offset = url_for(controller='feed', action='group',
                             id=group['name']) + '?page=-2'
        res = app.get(offset, status=400)
        assert '"page" parameter must be a positive integer' in res, res

    def test_atom_feed_page_not_int_gives_error(self):
        group = factories.Group()

        app = self._get_test_app()
        with app.flask_app.test_request_context():
            offset = url_for(controller='feed', action='group',
                             id=group['name']) + '?page=abc'
        res = app.get(offset, status=400)
        assert '"page" parameter must be a positive integer' in res, res
