# encoding: utf-8

import re

import nose.tools
from six import text_type

import ckan.tests.helpers as helpers
import ckan.tests.factories as factories
import ckan.logic as logic
import ckan.model as model
import ckan.plugins as p
import ckan.lib.jobs as jobs
import ckan.lib.search as search


assert_equals = nose.tools.assert_equals
assert_raises = nose.tools.assert_raises
eq = nose.tools.eq_
ok = nose.tools.ok_
raises = nose.tools.raises


class TestDelete:

    def setup(self):
        helpers.reset_db()

    def test_resource_delete(self):
        user = factories.User()
        sysadmin = factories.Sysadmin()
        resource = factories.Resource(user=user)
        context = {}
        params = {'id': resource['id']}

        helpers.call_action('resource_delete', context, **params)

        # Not even a sysadmin can see it now
        assert_raises(logic.NotFound, helpers.call_action, 'resource_show',
                      {'user': sysadmin['name']}, **params)
        # It is still there but with state=deleted
        res_obj = model.Resource.get(resource['id'])
        assert_equals(res_obj.state, 'deleted')


class TestDeleteResourceViews(object):

    @classmethod
    def setup_class(cls):
        if not p.plugin_loaded('image_view'):
            p.load('image_view')

        helpers.reset_db()

    @classmethod
    def teardown_class(cls):
        p.unload('image_view')

    def test_resource_view_delete(self):
        resource_view = factories.ResourceView()

        params = {'id': resource_view['id']}

        helpers.call_action('resource_view_delete', context={}, **params)

        assert_raises(logic.NotFound, helpers.call_action,
                      'resource_view_show',
                      context={}, **params)

        # The model object is actually deleted
        resource_view_obj = model.ResourceView.get(resource_view['id'])
        assert_equals(resource_view_obj, None)

    def test_delete_no_id_raises_validation_error(self):

        params = {}

        assert_raises(logic.ValidationError, helpers.call_action,
                      'resource_view_delete',
                      context={}, **params)

    def test_delete_wrong_id_raises_not_found_error(self):

        params = {'id': 'does_not_exist'}

        assert_raises(logic.NotFound, helpers.call_action,
                      'resource_view_delete',
                      context={}, **params)


class TestClearResourceViews(object):

    @classmethod
    def setup_class(cls):
        if not p.plugin_loaded('image_view'):
            p.load('image_view')
        if not p.plugin_loaded('recline_view'):
            p.load('recline_view')

        helpers.reset_db()

    @classmethod
    def teardown_class(cls):
        p.unload('image_view')
        p.unload('recline_view')

    def test_resource_view_clear(self):
        factories.ResourceView(view_type='image_view')
        factories.ResourceView(view_type='image_view')

        factories.ResourceView(view_type='recline_view')
        factories.ResourceView(view_type='recline_view')

        count = model.Session.query(model.ResourceView).count()

        assert_equals(count, 4)

        helpers.call_action('resource_view_clear', context={})

        count = model.Session.query(model.ResourceView).count()

        assert_equals(count, 0)

    def test_resource_view_clear_with_types(self):
        factories.ResourceView(view_type='image_view')
        factories.ResourceView(view_type='image_view')

        factories.ResourceView(view_type='recline_view')
        factories.ResourceView(view_type='recline_view')

        count = model.Session.query(model.ResourceView).count()

        assert_equals(count, 4)

        helpers.call_action('resource_view_clear', context={},
                            view_types=['image_view'])

        view_types = model.Session.query(model.ResourceView.view_type).all()

        assert_equals(len(view_types), 2)
        for view_type in view_types:
            assert_equals(view_type[0], 'recline_view')


class TestDeleteTags(object):

    def test_tag_delete_with_unicode_returns_unicode_error(self):
        # There is not a lot of call for it, but in theory there could be
        # unicode in the ActionError error message, so ensure that comes
        # through in NotFound as unicode.
        try:
            helpers.call_action('tag_delete', id=u'Delta symbol: \u0394')
        except logic.NotFound as e:
            assert u'Delta symbol: \u0394' in text_type(e)
        else:
            assert 0, 'Should have raised NotFound'


class TestGroupPurge(object):
    def setup(self):
        helpers.reset_db()

    def test_a_non_sysadmin_cant_purge_group(self):
        user = factories.User()
        group = factories.Group(user=user)

        assert_raises(logic.NotAuthorized,
                      helpers.call_action,
                      'group_purge',
                      context={'user': user['name'], 'ignore_auth': False},
                      id=group['name'])

    def test_purged_group_does_not_show(self):
        group = factories.Group()

        helpers.call_action('group_purge', id=group['name'])

        assert_raises(logic.NotFound, helpers.call_action, 'group_show',
                      context={}, id=group['name'])

    def test_purged_group_is_not_listed(self):
        group = factories.Group()

        helpers.call_action('group_purge', id=group['name'])

        assert_equals(helpers.call_action('group_list', context={}), [])

    def test_dataset_in_a_purged_group_no_longer_shows_that_group(self):
        group = factories.Group()
        dataset = factories.Dataset(groups=[{'name': group['name']}])

        helpers.call_action('group_purge', id=group['name'])

        dataset_shown = helpers.call_action('package_show', context={},
                                            id=dataset['id'])
        assert_equals(dataset_shown['groups'], [])

    def test_purged_group_is_not_in_search_results_for_its_ex_dataset(self):
        search.clear_all()
        group = factories.Group()
        dataset = factories.Dataset(groups=[{'name': group['name']}])

        def get_search_result_groups():
            results = helpers.call_action('package_search',
                                          q=dataset['title'])['results']
            return [g['name'] for g in results[0]['groups']]
        assert_equals(get_search_result_groups(), [group['name']])

        helpers.call_action('group_purge', id=group['name'])

        assert_equals(get_search_result_groups(), [])

    def test_purged_group_leaves_no_trace_in_the_model(self):
        factories.Group(name='parent')
        user = factories.User()
        group1 = factories.Group(name='group1',
                                 extras=[{'key': 'key1', 'value': 'val1'}],
                                 users=[{'name': user['name']}],
                                 groups=[{'name': 'parent'}])
        factories.Dataset(name='ds', groups=[{'name': 'group1'}])
        factories.Group(name='child', groups=[{'name': 'group1'}])
        num_revisions_before = model.Session.query(model.Revision).count()

        helpers.call_action('group_purge', id=group1['name'])
        num_revisions_after = model.Session.query(model.Revision).count()

        # the Group and related objects are gone
        assert_equals(sorted([g.name for g in
                              model.Session.query(model.Group).all()]),
                      ['child', 'parent'])
        assert_equals(model.Session.query(model.GroupExtra).all(), [])
        # the only members left are the users for the parent and child
        assert_equals(sorted([
            (m.table_name, m.group.name)
            for m in model.Session.query(model.Member).join(model.Group)]),
            [('user', 'child'), ('user', 'parent')])
        # the dataset is still there though
        assert_equals([p.name for p in model.Session.query(model.Package)],
                      ['ds'])

        # the group's object revisions were purged too
        assert_equals(sorted(
            [gr.name for gr in model.Session.query(model.GroupRevision)]),
            ['child', 'parent'])
        assert_equals(model.Session.query(model.GroupExtraRevision).all(),
                      [])
        # Member is not revisioned

        # No Revision objects were purged, in fact 1 is created for the purge
        assert_equals(num_revisions_after - num_revisions_before, 1)

    def test_missing_id_returns_error(self):
        assert_raises(logic.ValidationError,
                      helpers.call_action, 'group_purge')

    def test_bad_id_returns_404(self):
        assert_raises(logic.NotFound,
                      helpers.call_action, 'group_purge', id='123')


class TestOrganizationPurge(object):
    def setup(self):
        helpers.reset_db()

    def test_a_non_sysadmin_cant_purge_org(self):
        user = factories.User()
        org = factories.Organization(user=user)

        assert_raises(logic.NotAuthorized,
                      helpers.call_action,
                      'organization_purge',
                      context={'user': user['name'], 'ignore_auth': False},
                      id=org['name'])

    def test_purged_org_does_not_show(self):
        org = factories.Organization()

        helpers.call_action('organization_purge', id=org['name'])

        assert_raises(logic.NotFound, helpers.call_action, 'organization_show',
                      context={}, id=org['name'])

    def test_purged_org_is_not_listed(self):
        org = factories.Organization()

        helpers.call_action('organization_purge', id=org['name'])

        assert_equals(helpers.call_action('organization_list', context={}), [])

    def test_dataset_in_a_purged_org_no_longer_shows_that_org(self):
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org['id'])

        helpers.call_action('organization_purge', id=org['name'])

        dataset_shown = helpers.call_action('package_show', context={},
                                            id=dataset['id'])
        assert_equals(dataset_shown['owner_org'], None)

    def test_purged_org_is_not_in_search_results_for_its_ex_dataset(self):
        search.clear_all()
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org['id'])

        def get_search_result_owner_org():
            results = helpers.call_action('package_search',
                                          q=dataset['title'])['results']
            return results[0]['owner_org']
        assert_equals(get_search_result_owner_org(), org['id'])

        helpers.call_action('organization_purge', id=org['name'])

        assert_equals(get_search_result_owner_org(), None)

    def test_purged_organization_leaves_no_trace_in_the_model(self):
        factories.Organization(name='parent')
        user = factories.User()
        org1 = factories.Organization(
            name='org1',
            extras=[{'key': 'key1', 'value': 'val1'}],
            users=[{'name': user['name']}],
            groups=[{'name': 'parent'}])
        factories.Dataset(name='ds', owner_org=org1['id'])
        factories.Organization(name='child', groups=[{'name': 'org1'}])
        num_revisions_before = model.Session.query(model.Revision).count()

        helpers.call_action('organization_purge', id=org1['name'])
        num_revisions_after = model.Session.query(model.Revision).count()

        # the Organization and related objects are gone
        assert_equals(sorted([o.name for o in
                              model.Session.query(model.Group).all()]),
                      ['child', 'parent'])
        assert_equals(model.Session.query(model.GroupExtra).all(), [])
        # the only members left are the users for the parent and child
        assert_equals(sorted([
            (m.table_name, m.group.name)
            for m in model.Session.query(model.Member).join(model.Group)]),
            [('user', 'child'), ('user', 'parent')])
        # the dataset is still there though
        assert_equals([p.name for p in model.Session.query(model.Package)],
                      ['ds'])

        # the organization's object revisions were purged too
        assert_equals(sorted(
            [gr.name for gr in model.Session.query(model.GroupRevision)]),
            ['child', 'parent'])
        assert_equals(model.Session.query(model.GroupExtraRevision).all(),
                      [])
        # Member is not revisioned

        # No Revision objects were purged, in fact 1 is created for the purge
        assert_equals(num_revisions_after - num_revisions_before, 1)

    def test_missing_id_returns_error(self):
        assert_raises(logic.ValidationError,
                      helpers.call_action, 'organization_purge')

    def test_bad_id_returns_404(self):
        assert_raises(logic.NotFound,
                      helpers.call_action, 'organization_purge', id='123')


class TestDatasetPurge(object):
    def setup(self):
        helpers.reset_db()

    def test_a_non_sysadmin_cant_purge_dataset(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)

        assert_raises(logic.NotAuthorized,
                      helpers.call_action,
                      'dataset_purge',
                      context={'user': user['name'], 'ignore_auth': False},
                      id=dataset['name'])

    def test_purged_dataset_does_not_show(self):
        dataset = factories.Dataset()

        helpers.call_action('dataset_purge',
                            context={'ignore_auth': True},
                            id=dataset['name'])

        assert_raises(logic.NotFound, helpers.call_action, 'package_show',
                      context={}, id=dataset['name'])

    def test_purged_dataset_is_not_listed(self):
        dataset = factories.Dataset()

        helpers.call_action('dataset_purge', id=dataset['name'])

        assert_equals(helpers.call_action('package_list', context={}), [])

    def test_group_no_longer_shows_its_purged_dataset(self):
        group = factories.Group()
        dataset = factories.Dataset(groups=[{'name': group['name']}])

        helpers.call_action('dataset_purge', id=dataset['name'])

        dataset_shown = helpers.call_action('group_show', context={},
                                            id=group['id'],
                                            include_datasets=True)
        assert_equals(dataset_shown['packages'], [])

    def test_purged_dataset_is_not_in_search_results(self):
        search.clear_all()
        dataset = factories.Dataset()

        def get_search_results():
            results = helpers.call_action('package_search',
                                          q=dataset['title'])['results']
            return [d['name'] for d in results]
        assert_equals(get_search_results(), [dataset['name']])

        helpers.call_action('dataset_purge', id=dataset['name'])

        assert_equals(get_search_results(), [])

    def test_purged_dataset_leaves_no_trace_in_the_model(self):
        factories.Group(name='group1')
        org = factories.Organization()
        dataset = factories.Dataset(
            tags=[{'name': 'tag1'}],
            groups=[{'name': 'group1'}],
            owner_org=org['id'],
            extras=[{'key': 'testkey', 'value': 'testvalue'}])
        factories.Resource(package_id=dataset['id'])
        num_revisions_before = model.Session.query(model.Revision).count()

        helpers.call_action('dataset_purge',
                            context={'ignore_auth': True},
                            id=dataset['name'])
        num_revisions_after = model.Session.query(model.Revision).count()

        # the Package and related objects are gone
        assert_equals(model.Session.query(model.Package).all(), [])
        assert_equals(model.Session.query(model.Resource).all(), [])
        assert_equals(model.Session.query(model.PackageTag).all(), [])
        # there is no clean-up of the tag object itself, just the PackageTag.
        assert_equals([t.name for t in model.Session.query(model.Tag).all()],
                      ['tag1'])
        assert_equals(model.Session.query(model.PackageExtra).all(), [])
        # the only member left is for the user created in factories.Group() and
        # factories.Organization()
        assert_equals(sorted(
            [(m.table_name, m.group.name)
             for m in model.Session.query(model.Member).join(model.Group)]),
            [('user', 'group1'), ('user', org['name'])])

        # all the object revisions were purged too
        assert_equals(model.Session.query(model.PackageRevision).all(), [])
        assert_equals(model.Session.query(model.ResourceRevision).all(), [])
        assert_equals(model.Session.query(model.PackageTagRevision).all(), [])
        assert_equals(model.Session.query(model.PackageExtraRevision).all(),
                      [])
        # Member is not revisioned

        # No Revision objects were purged or created
        assert_equals(num_revisions_after - num_revisions_before, 0)

    def test_purged_dataset_removed_from_relationships(self):
        child = factories.Dataset()
        parent = factories.Dataset()
        grandparent = factories.Dataset()

        helpers.call_action('package_relationship_create',
                            subject=child['id'],
                            type='child_of',
                            object=parent['id'])

        helpers.call_action('package_relationship_create',
                            subject=parent['id'],
                            type='child_of',
                            object=grandparent['id'])

        assert_equals(len(
            model.Session.query(model.PackageRelationship).all()), 2)

        helpers.call_action('dataset_purge',
                            context={'ignore_auth': True},
                            id=parent['name'])

        assert_equals(model.Session.query(model.PackageRelationship).all(), [])

    def test_missing_id_returns_error(self):
        assert_raises(logic.ValidationError,
                      helpers.call_action, 'dataset_purge')

    def test_bad_id_returns_404(self):
        assert_raises(logic.NotFound,
                      helpers.call_action, 'dataset_purge', id='123')


class TestUserDelete(object):
    def setup(self):
        helpers.reset_db()

    def test_user_delete(self):
        user = factories.User()
        context = {}
        params = {u'id': user[u'id']}

        helpers.call_action(u'user_delete', context, **params)

        # It is still there but with state=deleted
        user_obj = model.User.get(user[u'id'])
        assert_equals(user_obj.state, u'deleted')

    def test_user_delete_but_user_doesnt_exist(self):
        context = {}
        params = {u'id': 'unknown'}

        assert_raises(
            logic.NotFound,
            helpers.call_action,
            u'user_delete', context, **params)

    def test_user_delete_removes_memberships(self):
        user = factories.User()
        factories.Organization(
            users=[{u'name': user[u'id'], u'capacity': u'admin'}])

        factories.Group(
            users=[{u'name': user[u'id'], u'capacity': u'admin'}])

        user_memberships = model.Session.query(model.Member).filter(
            model.Member.table_id == user[u'id']).all()

        assert_equals(len(user_memberships), 2)

        assert_equals([m.state for m in user_memberships],
                      [u'active', u'active'])

        context = {}
        params = {u'id': user[u'id']}

        helpers.call_action(u'user_delete', context, **params)

        user_memberships = model.Session.query(model.Member).filter(
            model.Member.table_id == user[u'id']).all()

        # Member objects are still there, but flagged as deleted
        assert_equals(len(user_memberships), 2)

        assert_equals([m.state for m in user_memberships],
                      [u'deleted', u'deleted'])

    def test_user_delete_removes_memberships_when_using_name(self):
        user = factories.User()
        factories.Organization(
            users=[{u'name': user[u'id'], u'capacity': u'admin'}])

        factories.Group(
            users=[{u'name': user[u'id'], u'capacity': u'admin'}])

        context = {}
        params = {u'id': user[u'name']}

        helpers.call_action(u'user_delete', context, **params)

        user_memberships = model.Session.query(model.Member).filter(
            model.Member.table_id == user[u'id']).all()

        # Member objects are still there, but flagged as deleted
        assert_equals(len(user_memberships), 2)

        assert_equals([m.state for m in user_memberships],
                      [u'deleted', u'deleted'])


class TestJobClear(helpers.FunctionalRQTestBase):

    def test_all_queues(self):
        '''
        Test clearing all queues.
        '''
        self.enqueue()
        self.enqueue(queue=u'q')
        self.enqueue(queue=u'q')
        self.enqueue(queue=u'q')
        queues = helpers.call_action(u'job_clear')
        eq({jobs.DEFAULT_QUEUE_NAME, u'q'}, set(queues))
        all_jobs = self.all_jobs()
        eq(len(all_jobs), 0)

    def test_specific_queues(self):
        '''
        Test clearing specific queues.
        '''
        job1 = self.enqueue()
        job2 = self.enqueue(queue=u'q1')
        job3 = self.enqueue(queue=u'q1')
        job4 = self.enqueue(queue=u'q2')
        with helpers.recorded_logs(u'ckan.logic') as logs:
            queues = helpers.call_action(u'job_clear', queues=[u'q1', u'q2'])
        eq({u'q1', u'q2'}, set(queues))
        all_jobs = self.all_jobs()
        eq(len(all_jobs), 1)
        eq(all_jobs[0], job1)
        logs.assert_log(u'info', u'q1')
        logs.assert_log(u'info', u'q2')


class TestJobCancel(helpers.FunctionalRQTestBase):

    def test_existing_job(self):
        '''
        Test cancelling an existing job.
        '''
        job1 = self.enqueue(queue=u'q')
        job2 = self.enqueue(queue=u'q')
        with helpers.recorded_logs(u'ckan.logic') as logs:
            helpers.call_action(u'job_cancel', id=job1.id)
        all_jobs = self.all_jobs()
        eq(len(all_jobs), 1)
        eq(all_jobs[0], job2)
        assert_raises(KeyError, jobs.job_from_id, job1.id)
        logs.assert_log(u'info', re.escape(job1.id))

    @raises(logic.NotFound)
    def test_not_existing_job(self):
        helpers.call_action(u'job_cancel', id=u'does-not-exist')
