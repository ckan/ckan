from nose.tools import assert_equal

from ckan.lib.dictization import model_dictize
from ckan import model
from ckan.lib import search

from ckan.new_tests import helpers, factories


class TestDictize:

    def setup(self):
        helpers.reset_db()
        search.clear()

    def test_group_list_dictize(self):
        group = factories.Group()
        group_list = model.Session.query(model.Group).filter_by().all()
        context = {'model': model, 'session': model.Session}

        group_dicts = model_dictize.group_list_dictize(group_list, context)

        assert_equal(len(group_dicts), 1)
        assert_equal(group_dicts[0]['name'], group['name'])
        assert_equal(group_dicts[0]['packages'], 0)
        assert 'extras' not in group_dicts[0]
        assert 'tags' not in group_dicts[0]
        assert 'groups' not in group_dicts[0]

    def test_group_list_dictize_sorted(self):
        factories.Group(name='aa')
        factories.Group(name='bb')
        group_list = [model.Group.get(u'bb'),
                      model.Group.get(u'aa')]
        context = {'model': model, 'session': model.Session}

        group_dicts = model_dictize.group_list_dictize(group_list, context)

        # list is resorted by name
        assert_equal(group_dicts[0]['name'], 'aa')
        assert_equal(group_dicts[1]['name'], 'bb')

    def test_group_list_dictize_reverse_sorted(self):
        factories.Group(name='aa')
        factories.Group(name='bb')
        group_list = [model.Group.get(u'aa'),
                      model.Group.get(u'bb')]
        context = {'model': model, 'session': model.Session}

        group_dicts = model_dictize.group_list_dictize(group_list, context,
                                                       reverse=True)

        assert_equal(group_dicts[0]['name'], 'bb')
        assert_equal(group_dicts[1]['name'], 'aa')

    def test_group_list_dictize_without_package_count(self):
        group = factories.Group()
        factories.Dataset(group=group['name'])
        group_list = [model.Group.get(group['name'])]
        context = {'model': model, 'session': model.Session}

        group_dicts = model_dictize.group_list_dictize(
            group_list, context, with_package_counts=False)

        assert 'packages' not in group_dicts[0]

    def test_group_list_dictize_including_extras(self):
        factories.Group(extras=[{'key': 'k1', 'value': 'v1'}])
        group_list = model.Session.query(model.Group).filter_by().all()
        context = {'model': model, 'session': model.Session}

        group_dicts = model_dictize.group_list_dictize(group_list, context,
                                                       include_extras=True)

        assert_equal(group_dicts[0]['extras'][0]['key'], 'k1')

    def test_group_list_dictize_including_tags(self):
        factories.Group()
        # group tags aren't in the group_create schema, so its slightly more
        # convoluted way to create them
        group_obj = model.Session.query(model.Group).first()
        tag = model.Tag(name='t1')
        model.Session.add(tag)
        model.Session.commit()
        tag = model.Session.query(model.Tag).first()
        group_obj = model.Session.query(model.Group).first()
        member = model.Member(group=group_obj, table_id=tag.id,
                              table_name='tag')
        model.Session.add(member)
        model.repo.new_revision()
        model.Session.commit()
        group_list = model.Session.query(model.Group).filter_by().all()
        context = {'model': model, 'session': model.Session}

        group_dicts = model_dictize.group_list_dictize(group_list, context,
                                                       include_tags=True)

        assert_equal(group_dicts[0]['tags'][0]['name'], 't1')

    def test_group_list_dictize_including_groups(self):
        factories.Group(name='parent')
        factories.Group(name='child', groups=[{'name': 'parent'}])
        group_list = [model.Group.get(u'parent'), model.Group.get(u'child')]
        context = {'model': model, 'session': model.Session}

        child_dict, parent_dict = model_dictize.group_list_dictize(
            group_list, context, include_groups=True)

        assert_equal(parent_dict['name'], 'parent')
        assert_equal(child_dict['name'], 'child')
        assert_equal(parent_dict['groups'], [])
        assert_equal(child_dict['groups'][0]['name'], 'parent')

    def test_group_dictize(self):
        group = factories.Group()
        factories.Dataset(group=group['name'])
        group_obj = model.Session.query(model.Group).filter_by().first()
        context = {'model': model, 'session': model.Session}

        group = model_dictize.group_dictize(group_obj, context)

        assert_equal(group['name'], 'test_group_0')
        assert_equal(group['packages'], [])
        assert_equal(group['extras'], [])
        assert_equal(group['tags'], [])
        assert_equal(group['groups'], [])

    def test_group_dictize_without_packages(self):
        # group_list_dictize might not be interested in packages at all
        # so sets these options. e.g. it is not all_fields nor are the results
        # sorted by the number of packages.
        factories.Group()
        group_obj = model.Session.query(model.Group).filter_by().first()
        context = {'model': model, 'session': model.Session}

        group = model_dictize.group_dictize(group_obj, context,
                                            packages_field=None)

        assert 'packages' not in group

    def test_group_dictize_with_package_list(self):
        group_ = factories.Group()
        package = factories.Dataset(groups=[{'name': group_['name']}])
        group_obj = model.Session.query(model.Group).filter_by().first()
        context = {'model': model, 'session': model.Session}

        group = model_dictize.group_dictize(group_obj, context)

        assert_equal(type(group['packages']), list)
        assert_equal(len(group['packages']), 1)
        assert_equal(group['packages'][0]['name'], package['name'])

    def test_group_dictize_with_package_count(self):
        # group_list_dictize calls it like this by default
        group_ = factories.Group()
        factories.Dataset(groups=[{'name': group_['name']}])
        group_obj = model.Session.query(model.Group).filter_by().first()
        context = {'model': model, 'session': model.Session,
                   'dataset_counts': model_dictize.get_group_dataset_counts()
                   }

        group = model_dictize.group_dictize(group_obj, context,
                                            packages_field='dataset_count')

        assert_equal(group['packages'], 1)
        assert_equal(group['package_count'], 1)

    def test_group_dictize_with_no_packages_field_but_still_package_count(self):
        # logic.get.group_show calls it like this when not include_datasets
        group_ = factories.Group()
        factories.Dataset(groups=[{'name': group_['name']}])
        group_obj = model.Session.query(model.Group).filter_by().first()
        context = {'model': model, 'session': model.Session}
        # not supplying dataset_counts in this case either

        group = model_dictize.group_dictize(group_obj, context,
                                            packages_field=
                                            'none_but_include_package_count')

        assert 'packages' not in group
        assert_equal(group['package_count'], 1)

    def test_group_dictize_for_org_with_package_list(self):
        org_ = factories.Organization()
        package = factories.Dataset(owner_org=org_['id'])
        group_obj = model.Session.query(model.Group).filter_by().first()
        context = {'model': model, 'session': model.Session}

        org = model_dictize.group_dictize(group_obj, context)

        assert_equal(type(org['packages']), list)
        assert_equal(len(org['packages']), 1)
        assert_equal(org['packages'][0]['name'], package['name'])

    def test_group_dictize_for_org_with_package_count(self):
        # group_list_dictize calls it like this by default
        org_ = factories.Organization()
        factories.Dataset(owner_org=org_['id'])
        org_obj = model.Session.query(model.Group).filter_by().first()
        context = {'model': model, 'session': model.Session,
                   'dataset_counts': model_dictize.get_group_dataset_counts()
                   }

        org = model_dictize.group_dictize(org_obj, context,
                                          packages_field='dataset_count')

        assert_equal(org['packages'], 1)
