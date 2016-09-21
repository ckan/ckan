# encoding: utf-8

from routes import url_for

import ckan.tests.helpers as helpers
import ckan.tests.factories as factories


class TestFeedNew(helpers.FunctionalTestBase):

    @classmethod
    def teardown_class(cls):
        helpers.reset_db()

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

    def test_general_atom_feed_works(self):
        dataset = factories.Dataset()
        offset = url_for(controller='feed', action='general')
        app = self._get_test_app()
        res = app.get(offset)

        assert '<title>{0}</title>'.format(dataset['title']) in res.body

    def test_group_atom_feed_works(self):
        group = factories.Group()
        dataset = factories.Dataset(groups=[{'id': group['id']}])
        offset = url_for(controller='feed', action='group',
                         id=group['name'])
        app = self._get_test_app()
        res = app.get(offset)

        assert '<title>{0}</title>'.format(dataset['title']) in res.body

    def test_organization_atom_feed_works(self):
        group = factories.Organization()
        dataset = factories.Dataset(owner_org=group['id'])
        offset = url_for(controller='feed', action='organization',
                         id=group['name'])
        app = self._get_test_app()
        res = app.get(offset)

        assert '<title>{0}</title>'.format(dataset['title']) in res.body

    def test_custom_atom_feed_works(self):
        dataset1 = factories.Dataset(
            title='Test weekly',
            extras=[{'key': 'frequency', 'value': 'weekly'}])
        dataset2 = factories.Dataset(
            title='Test daily',
            extras=[{'key': 'frequency', 'value': 'daily'}])
        offset = url_for(controller='feed', action='custom')
        params = {
            'q': 'frequency:weekly'
        }
        app = self._get_test_app()
        res = app.get(offset, params=params)

        assert '<title>{0}</title>'.format(dataset1['title']) in res.body

        assert '<title>{0}</title>'.format(dataset2['title']) not in res.body
