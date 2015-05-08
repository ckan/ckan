from routes import url_for

from ckan import model
import ckan.tests.helpers as helpers
import ckan.tests.factories as factories


class TestFeedNew(helpers.FunctionalTestBase):

    def test_atom_feed_page_zero_gives_error(self):
        group = factories.Group()
        offset = url_for(controller='feed', action='group',
                         id=group['name']) + '?page=0'
        app = self._get_test_app()
        res = app.get(offset, status=400)
        assert '"page" parameter must be a positive integer' in res, res

    def test_atom_feed_page_negative_gives_error(self):
        group = factories.Group()
        offset = url_for(controller='feed', action='group',
                         id=group['name']) + '?page=-2'
        app = self._get_test_app()
        res = app.get(offset, status=400)
        assert '"page" parameter must be a positive integer' in res, res

    def test_atom_feed_page_not_int_gives_error(self):
        group = factories.Group()
        offset = url_for(controller='feed', action='group',
                         id=group['name']) + '?page=abc'
        app = self._get_test_app()
        res = app.get(offset, status=400)
        assert '"page" parameter must be a positive integer' in res, res
