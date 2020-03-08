import pytest

from ckan import model, logic
from ckan.tests import helpers, factories


@pytest.mark.ckan_config('ckan.plugins', 'datastore')
@pytest.mark.usefixtures('clean_db', 'with_plugins')
class TestCollaboratorsDataStore():

    def _get_context(self, user):

        return {
            'model': model,
            'user': user if isinstance(user, basestring) else user.get('name')
        }

    def test_datastore_search_private_editor(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org['id'])
        resource = factories.Resource(package_id=dataset['id'])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'datastore_search',
                context=context, resource_id=resource['id'])

        helpers.call_action(
            'package_member_create',
            id=dataset['id'], user_id=user['id'], capacity='editor')

        assert helpers.call_auth(
            'datastore_search',
            context=context, resource_id=resource['id'])

    def test_datastore_search_private_member(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org['id'])
        resource = factories.Resource(package_id=dataset['id'])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'datastore_search',
                context=context, resource_id=resource['id'])

        helpers.call_action(
            'package_member_create',
            id=dataset['id'], user_id=user['id'], capacity='member')

        assert helpers.call_auth(
            'datastore_search',
            context=context, resource_id=resource['id'])

    def test_datastore_info_private_editor(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org['id'])
        resource = factories.Resource(package_id=dataset['id'])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'datastore_info',
                context=context, resource_id=resource['id'])

        helpers.call_action(
            'package_member_create',
            id=dataset['id'], user_id=user['id'], capacity='editor')

        assert helpers.call_auth(
            'datastore_info',
            context=context, resource_id=resource['id'])

    def test_datastore_info_private_member(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org['id'])
        resource = factories.Resource(package_id=dataset['id'])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'datastore_info',
                context=context, resource_id=resource['id'])

        helpers.call_action(
            'package_member_create',
            id=dataset['id'], user_id=user['id'], capacity='member')

        assert helpers.call_auth(
            'datastore_info',
            context=context, resource_id=resource['id'])

    def test_datastore_search_sql_private_editor(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org['id'])
        resource = factories.Resource(package_id=dataset['id'])
        user = factories.User()

        context = self._get_context(user)
        context['table_names'] = [resource['id']]
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'datastore_search_sql',
                context=context, sql='SELECT * FROM "{}"'.format(
                    resource['id']))

        helpers.call_action(
            'package_member_create',
            id=dataset['id'], user_id=user['id'], capacity='editor')

        assert helpers.call_auth(
            'datastore_search_sql',
            context=context, sql='SELECT * FROM "{}"'.format(resource['id']))

    def test_datastore_search_sql_private_member(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org['id'])
        resource = factories.Resource(package_id=dataset['id'])
        user = factories.User()

        context = self._get_context(user)
        context['table_names'] = [resource['id']]
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'datastore_search_sql',
                context=context, sql='SELECT * FROM "{}"'.format(
                    resource['id']))

        helpers.call_action(
            'package_member_create',
            id=dataset['id'], user_id=user['id'], capacity='member')

        assert helpers.call_auth(
            'datastore_search_sql',
            context=context, sql='SELECT * FROM "{}"'.format(resource['id']))

    def test_datastore_create_private_editor(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org['id'])
        resource = factories.Resource(package_id=dataset['id'])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'datastore_create',
                context=context, resource_id=resource['id'])

        helpers.call_action(
            'package_member_create',
            id=dataset['id'], user_id=user['id'], capacity='editor')

        assert helpers.call_auth(
            'datastore_create',
            context=context, resource_id=resource['id'])

    def test_datastore_create_private_member(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org['id'])
        resource = factories.Resource(package_id=dataset['id'])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'datastore_create',
                context=context, resource_id=resource['id'])

        helpers.call_action(
            'package_member_create',
            id=dataset['id'], user_id=user['id'], capacity='member')

        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'datastore_create',
                context=context, resource_id=resource['id'])

    def test_datastore_upsert_private_editor(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org['id'])
        resource = factories.Resource(package_id=dataset['id'])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'datastore_upsert',
                context=context, resource_id=resource['id'])

        helpers.call_action(
            'package_member_create',
            id=dataset['id'], user_id=user['id'], capacity='editor')

        assert helpers.call_auth(
            'datastore_upsert',
            context=context, resource_id=resource['id'])

    def test_datastore_upsert_private_member(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org['id'])
        resource = factories.Resource(package_id=dataset['id'])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'datastore_upsert',
                context=context, resource_id=resource['id'])

        helpers.call_action(
            'package_member_create',
            id=dataset['id'], user_id=user['id'], capacity='member')

        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'datastore_upsert',
                context=context, resource_id=resource['id'])

    def test_datastore_delete_private_editor(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org['id'])
        resource = factories.Resource(package_id=dataset['id'])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'datastore_delete',
                context=context, resource_id=resource['id'])

        helpers.call_action(
            'package_member_create',
            id=dataset['id'], user_id=user['id'], capacity='editor')

        assert helpers.call_auth(
            'datastore_delete',
            context=context, resource_id=resource['id'])

    def test_datastore_delete_private_member(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org['id'])
        resource = factories.Resource(package_id=dataset['id'])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'datastore_delete',
                context=context, resource_id=resource['id'])

        helpers.call_action(
            'package_member_create',
            id=dataset['id'], user_id=user['id'], capacity='member')

        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                'datastore_delete',
                context=context, resource_id=resource['id'])
