# encoding: utf-8

import pytest
from six import string_types
from ckan import model, logic
from ckan.tests import helpers, factories


@pytest.mark.ckan_config(u'ckan.plugins', u'datastore')
@pytest.mark.usefixtures(u'clean_db', u'with_plugins')
@pytest.mark.ckan_config(u'ckan.auth.allow_dataset_collaborators', True)
class TestCollaboratorsDataStore():

    def _get_context(self, user):

        return {
            u'model': model,
            u'user': user if isinstance(user, string_types) else user.get(u'name')
        }

    def test_datastore_search_private_editor(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org[u'id'])
        resource = factories.Resource(package_id=dataset[u'id'])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                u'datastore_search',
                context=context, resource_id=resource[u'id'])

        helpers.call_action(
            u'package_collaborator_create',
            id=dataset[u'id'], user_id=user[u'id'], capacity=u'editor')

        assert helpers.call_auth(
            u'datastore_search',
            context=context, resource_id=resource[u'id'])

    def test_datastore_search_private_member(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org[u'id'])
        resource = factories.Resource(package_id=dataset[u'id'])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                u'datastore_search',
                context=context, resource_id=resource[u'id'])

        helpers.call_action(
            u'package_collaborator_create',
            id=dataset[u'id'], user_id=user[u'id'], capacity=u'member')

        assert helpers.call_auth(
            u'datastore_search',
            context=context, resource_id=resource[u'id'])

    def test_datastore_info_private_editor(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org[u'id'])
        resource = factories.Resource(package_id=dataset[u'id'])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                u'datastore_info',
                context=context, resource_id=resource[u'id'])

        helpers.call_action(
            u'package_collaborator_create',
            id=dataset[u'id'], user_id=user[u'id'], capacity=u'editor')

        assert helpers.call_auth(
            u'datastore_info',
            context=context, resource_id=resource[u'id'])

    def test_datastore_info_private_member(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org[u'id'])
        resource = factories.Resource(package_id=dataset[u'id'])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                u'datastore_info',
                context=context, resource_id=resource[u'id'])

        helpers.call_action(
            u'package_collaborator_create',
            id=dataset[u'id'], user_id=user[u'id'], capacity=u'member')

        assert helpers.call_auth(
            u'datastore_info',
            context=context, resource_id=resource[u'id'])

    def test_datastore_search_sql_private_editor(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org[u'id'])
        resource = factories.Resource(package_id=dataset[u'id'])
        user = factories.User()

        context = self._get_context(user)
        context[u'table_names'] = [resource[u'id']]
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                u'datastore_search_sql',
                context=context, sql=u'SELECT * FROM "{}"'.format(
                    resource[u'id']))

        helpers.call_action(
            u'package_collaborator_create',
            id=dataset[u'id'], user_id=user[u'id'], capacity=u'editor')

        assert helpers.call_auth(
            u'datastore_search_sql',
            context=context, sql=u'SELECT * FROM "{}"'.format(resource[u'id']))

    def test_datastore_search_sql_private_member(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org[u'id'])
        resource = factories.Resource(package_id=dataset[u'id'])
        user = factories.User()

        context = self._get_context(user)
        context[u'table_names'] = [resource[u'id']]
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                u'datastore_search_sql',
                context=context, sql=u'SELECT * FROM "{}"'.format(
                    resource[u'id']))

        helpers.call_action(
            u'package_collaborator_create',
            id=dataset[u'id'], user_id=user[u'id'], capacity=u'member')

        assert helpers.call_auth(
            u'datastore_search_sql',
            context=context, sql=u'SELECT * FROM "{}"'.format(resource[u'id']))

    def test_datastore_create_private_editor(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org[u'id'])
        resource = factories.Resource(package_id=dataset[u'id'])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                u'datastore_create',
                context=context, resource_id=resource[u'id'])

        helpers.call_action(
            u'package_collaborator_create',
            id=dataset[u'id'], user_id=user[u'id'], capacity=u'editor')

        assert helpers.call_auth(
            u'datastore_create',
            context=context, resource_id=resource[u'id'])

    def test_datastore_create_private_member(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org[u'id'])
        resource = factories.Resource(package_id=dataset[u'id'])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                u'datastore_create',
                context=context, resource_id=resource[u'id'])

        helpers.call_action(
            u'package_collaborator_create',
            id=dataset[u'id'], user_id=user[u'id'], capacity=u'member')

        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                u'datastore_create',
                context=context, resource_id=resource[u'id'])

    def test_datastore_upsert_private_editor(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org[u'id'])
        resource = factories.Resource(package_id=dataset[u'id'])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                u'datastore_upsert',
                context=context, resource_id=resource[u'id'])

        helpers.call_action(
            u'package_collaborator_create',
            id=dataset[u'id'], user_id=user[u'id'], capacity=u'editor')

        assert helpers.call_auth(
            u'datastore_upsert',
            context=context, resource_id=resource[u'id'])

    def test_datastore_upsert_private_member(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org[u'id'])
        resource = factories.Resource(package_id=dataset[u'id'])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                u'datastore_upsert',
                context=context, resource_id=resource[u'id'])

        helpers.call_action(
            u'package_collaborator_create',
            id=dataset[u'id'], user_id=user[u'id'], capacity=u'member')

        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                u'datastore_upsert',
                context=context, resource_id=resource[u'id'])

    def test_datastore_delete_private_editor(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org[u'id'])
        resource = factories.Resource(package_id=dataset[u'id'])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                u'datastore_delete',
                context=context, resource_id=resource[u'id'])

        helpers.call_action(
            u'package_collaborator_create',
            id=dataset[u'id'], user_id=user[u'id'], capacity=u'editor')

        assert helpers.call_auth(
            u'datastore_delete',
            context=context, resource_id=resource[u'id'])

    def test_datastore_delete_private_member(self):

        org = factories.Organization()
        dataset = factories.Dataset(private=True, owner_org=org[u'id'])
        resource = factories.Resource(package_id=dataset[u'id'])
        user = factories.User()

        context = self._get_context(user)
        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                u'datastore_delete',
                context=context, resource_id=resource[u'id'])

        helpers.call_action(
            u'package_collaborator_create',
            id=dataset[u'id'], user_id=user[u'id'], capacity=u'member')

        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                u'datastore_delete',
                context=context, resource_id=resource[u'id'])
