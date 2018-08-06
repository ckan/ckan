# encoding: utf-8

import datetime
import copy

from nose.tools import assert_equal

from ckan.lib.dictization import model_dictize, model_save
from ckan import model
from ckan.lib import search

from ckan.tests import helpers, factories


class TestGroupListDictize:

    def setup(self):
        helpers.reset_db()
        search.clear_all()

    def test_group_list_dictize(self):
        group = factories.Group()
        group_list = model.Session.query(model.Group).filter_by().all()
        context = {'model': model, 'session': model.Session}

        group_dicts = model_dictize.group_list_dictize(group_list, context)

        assert_equal(len(group_dicts), 1)
        assert_equal(group_dicts[0]['name'], group['name'])
        assert_equal(group_dicts[0]['package_count'], 0)
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

    def test_group_list_dictize_sort_by_package_count(self):
        factories.Group(name='aa')
        factories.Group(name='bb')
        factories.Dataset(groups=[{'name': 'aa'}, {'name': 'bb'}])
        factories.Dataset(groups=[{'name': 'bb'}])
        group_list = [model.Group.get(u'bb'),
                      model.Group.get(u'aa')]
        context = {'model': model, 'session': model.Session}

        group_dicts = model_dictize.group_list_dictize(
            group_list, context, sort_key=lambda x: x['package_count'],
            with_package_counts=True)

        # list is resorted by package counts
        assert_equal(group_dicts[0]['name'], 'aa')
        assert_equal(group_dicts[1]['name'], 'bb')

    def test_group_list_dictize_without_package_count(self):
        group_ = factories.Group()
        factories.Dataset(groups=[{'name': group_['name']}])
        group_list = [model.Group.get(group_['name'])]
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


class TestGroupDictize:

    def setup(self):
        helpers.reset_db()
        search.clear_all()

    def test_group_dictize(self):
        group = factories.Group(name='test_dictize')
        group_obj = model.Session.query(model.Group).filter_by().first()
        context = {'model': model, 'session': model.Session}

        group = model_dictize.group_dictize(group_obj, context)

        assert_equal(group['name'], 'test_dictize')
        assert_equal(group['packages'], [])
        assert_equal(group['extras'], [])
        assert_equal(group['tags'], [])
        assert_equal(group['groups'], [])

    def test_group_dictize_group_with_dataset(self):
        group_ = factories.Group()
        package = factories.Dataset(groups=[{'name': group_['name']}])
        group_obj = model.Session.query(model.Group).filter_by().first()
        context = {'model': model, 'session': model.Session}

        group = model_dictize.group_dictize(group_obj, context)

        assert_equal(group['packages'][0]['name'], package['name'])
        assert_equal(group['packages'][0]['groups'][0]['name'], group_['name'])

    def test_group_dictize_group_with_extra(self):
        factories.Group(extras=[{'key': 'k1', 'value': 'v1'}])
        group_obj = model.Session.query(model.Group).filter_by().first()
        context = {'model': model, 'session': model.Session}

        group = model_dictize.group_dictize(group_obj, context)

        assert_equal(group['extras'][0]['key'], 'k1')

    def test_group_dictize_group_with_parent_group(self):
        factories.Group(name='parent')
        factories.Group(name='child', groups=[{'name': 'parent'}])
        group_obj = model.Group.get('child')
        context = {'model': model, 'session': model.Session}

        group = model_dictize.group_dictize(group_obj, context)

        assert_equal(len(group['groups']), 1)
        assert_equal(group['groups'][0]['name'], 'parent')
        assert_equal(group['groups'][0]['package_count'], 0)

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

    def test_group_dictize_with_package_list_limited(self):
        '''
        Packages returned in group are limited by context var.
        '''
        group_ = factories.Group()
        for _ in range(10):
            factories.Dataset(groups=[{'name': group_['name']}])
        group_obj = model.Session.query(model.Group).filter_by().first()
        # limit packages to 4
        context = {'model': model, 'session': model.Session, 'limits': {'packages': 4}}

        group = model_dictize.group_dictize(group_obj, context)

        assert_equal(len(group['packages']), 4)

    def test_group_dictize_with_package_list_limited_over(self):
        '''
        Packages limit is set higher than number of packages in group.
        '''
        group_ = factories.Group()
        for _ in range(3):
            factories.Dataset(groups=[{'name': group_['name']}])
        group_obj = model.Session.query(model.Group).filter_by().first()
        # limit packages to 4
        context = {'model': model, 'session': model.Session, 'limits': {'packages': 4}}

        group = model_dictize.group_dictize(group_obj, context)

        assert_equal(len(group['packages']), 3)

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
        assert_equal(group['package_count'], 1)

    def test_group_dictize_with_no_packages_field_but_still_package_count(self):
        # logic.get.group_show calls it like this when not include_datasets
        group_ = factories.Group()
        factories.Dataset(groups=[{'name': group_['name']}])
        group_obj = model.Session.query(model.Group).filter_by().first()
        context = {'model': model, 'session': model.Session}
        # not supplying dataset_counts in this case either

        group = model_dictize.group_dictize(group_obj, context,
                                            packages_field='dataset_count')

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

        assert_equal(org['package_count'], 1)


class TestPackageDictize:

    def setup(self):
        helpers.reset_db()

    def remove_changable_values(self, dict_):
        dict_ = copy.deepcopy(dict_)
        for key, value in dict_.items():
            if key.endswith('id') and key != 'license_id':
                dict_.pop(key)
            if key == 'created':
                dict_.pop(key)
            if 'timestamp' in key:
                dict_.pop(key)
            if key in ['metadata_created', 'metadata_modified']:
                dict_.pop(key)
            if isinstance(value, list):
                for i, sub_dict in enumerate(value):
                    value[i] = self.remove_changable_values(sub_dict)
        return dict_

    def assert_equals_expected(self, expected_dict, result_dict):
        result_dict = self.remove_changable_values(result_dict)
        superfluous_keys = set(result_dict) - set(expected_dict)
        assert not superfluous_keys, 'Did not expect key: %s' % \
            ' '.join(('%s=%s' % (k, result_dict[k]) for k in superfluous_keys))
        for key in expected_dict:
            assert expected_dict[key] == result_dict[key], \
                '%s=%s should be %s' % \
                (key, result_dict[key], expected_dict[key])

    def test_package_dictize_basic(self):
        dataset = factories.Dataset(name='test_dataset_dictize',
                                    notes='Some *description*',
                                    url='http://example.com')
        dataset_obj = model.Package.get(dataset['id'])
        context = {'model': model, 'session': model.Session}

        result = model_dictize.package_dictize(dataset_obj, context)

        assert_equal(result['name'], dataset['name'])
        assert_equal(result['isopen'], False)
        assert_equal(result['type'], dataset['type'])
        today = datetime.date.today().strftime('%Y-%m-%d')
        assert result['metadata_modified'].startswith(today)
        assert result['metadata_created'].startswith(today)
        assert_equal(result['creator_user_id'], dataset_obj.creator_user_id)
        expected_dict = {
            'author': None,
            'author_email': None,
            'extras': [],
            'groups': [],
            'isopen': False,
            'license_id': None,
            'license_title': None,
            'maintainer': None,
            'maintainer_email': None,
            'name': u'test_dataset_dictize',
            'notes': 'Some *description*',
            'num_resources': 0,
            'num_tags': 0,
            'organization': None,
            'owner_org': None,
            'private': False,
            'relationships_as_object': [],
            'relationships_as_subject': [],
            'resources': [],
            'state': u'active',
            'tags': [],
            'title': u'Test Dataset',
            'type': u'dataset',
            'url': 'http://example.com',
            'version': None}
        self.assert_equals_expected(expected_dict, result)

    def test_package_dictize_license(self):
        dataset = factories.Dataset(license_id='cc-by')
        dataset_obj = model.Package.get(dataset['id'])
        context = {'model': model, 'session': model.Session}

        result = model_dictize.package_dictize(dataset_obj, context)

        assert_equal(result['isopen'], True)
        assert_equal(result['license_id'], 'cc-by')
        assert_equal(result['license_url'],
                     'http://www.opendefinition.org/licenses/cc-by')
        assert_equal(result['license_title'], 'Creative Commons Attribution')

    def test_package_dictize_title_stripped_of_whitespace(self):
        dataset = factories.Dataset(title=' has whitespace \t')
        dataset_obj = model.Package.get(dataset['id'])
        context = {'model': model, 'session': model.Session}

        result = model_dictize.package_dictize(dataset_obj, context)

        assert_equal(result['title'], 'has whitespace')
        assert_equal(dataset_obj.title, ' has whitespace \t')

    def test_package_dictize_resource(self):
        dataset = factories.Dataset()
        resource = factories.Resource(package_id=dataset['id'],
                                      name='test_pkg_dictize')
        dataset_obj = model.Package.get(dataset['id'])
        context = {'model': model, 'session': model.Session}

        result = model_dictize.package_dictize(dataset_obj, context)

        assert_equal_for_keys(result['resources'][0], resource, 'name', 'url')
        expected_dict = {
            u'cache_last_updated': None,
            u'cache_url': None,
            u'description': u'Just another test resource.',
            u'format': u'res_format',
            u'hash': u'',
            u'last_modified': None,
            u'mimetype': None,
            u'mimetype_inner': None,
            u'name': u'test_pkg_dictize',
            u'position': 0,
            u'resource_type': None,
            u'size': None,
            u'state': u'active',
            u'url': u'http://link.to.some.data',
            u'url_type': None
        }
        self.assert_equals_expected(expected_dict, result['resources'][0])

    def test_package_dictize_resource_upload_and_striped(self):
        dataset = factories.Dataset()
        resource = factories.Resource(package=dataset['id'],
                                      name='test_pkg_dictize',
                                      url_type='upload',
                                      url='some_filename.csv')

        context = {'model': model, 'session': model.Session}

        result = model_save.resource_dict_save(resource, context)

        expected_dict = {
            u'url': u'some_filename.csv',
            u'url_type': u'upload'
        }
        assert expected_dict['url'] == result.url

    def test_package_dictize_resource_upload_with_url_and_striped(self):
        dataset = factories.Dataset()
        resource = factories.Resource(package=dataset['id'],
                                      name='test_pkg_dictize',
                                      url_type='upload',
                                      url='http://some_filename.csv')

        context = {'model': model, 'session': model.Session}

        result = model_save.resource_dict_save(resource, context)

        expected_dict = {
            u'url': u'some_filename.csv',
            u'url_type': u'upload'
        }
        assert expected_dict['url'] == result.url

    def test_package_dictize_tags(self):
        dataset = factories.Dataset(tags=[{'name': 'fish'}])
        dataset_obj = model.Package.get(dataset['id'])
        context = {'model': model, 'session': model.Session}

        result = model_dictize.package_dictize(dataset_obj, context)

        assert_equal(result['tags'][0]['name'], 'fish')
        expected_dict = {'display_name': u'fish',
                         u'name': u'fish',
                         u'state': u'active'}
        self.assert_equals_expected(expected_dict, result['tags'][0])

    def test_package_dictize_extras(self):
        extras_dict = {'key': 'latitude', 'value': '54.6'}
        dataset = factories.Dataset(extras=[extras_dict])
        dataset_obj = model.Package.get(dataset['id'])
        context = {'model': model, 'session': model.Session}

        result = model_dictize.package_dictize(dataset_obj, context)

        assert_equal_for_keys(result['extras'][0], extras_dict,
                              'key', 'value')
        expected_dict = {u'key': u'latitude',
                         u'state': u'active',
                         u'value': u'54.6'}
        self.assert_equals_expected(expected_dict, result['extras'][0])

    def test_package_dictize_group(self):
        group = factories.Group(name='test_group_dictize',
                                title='Test Group Dictize')
        dataset = factories.Dataset(groups=[{'name': group['name']}])
        dataset_obj = model.Package.get(dataset['id'])
        context = {'model': model, 'session': model.Session}

        result = model_dictize.package_dictize(dataset_obj, context)

        assert_equal_for_keys(result['groups'][0], group,
                              'name')
        expected_dict = {
            u'approval_status': u'approved',
            u'capacity': u'public',
            u'description': u'A test description for this test group.',
            'display_name': u'Test Group Dictize',
            'image_display_url': u'',
            u'image_url': u'',
            u'is_organization': False,
            u'name': u'test_group_dictize',
            u'state': u'active',
            u'title': u'Test Group Dictize',
            u'type': u'group'}
        self.assert_equals_expected(expected_dict, result['groups'][0])

    def test_package_dictize_owner_org(self):
        org = factories.Organization(name='test_package_dictize')
        dataset = factories.Dataset(owner_org=org['id'])
        dataset_obj = model.Package.get(dataset['id'])
        context = {'model': model, 'session': model.Session}

        result = model_dictize.package_dictize(dataset_obj, context)

        assert_equal(result['owner_org'], org['id'])
        assert_equal_for_keys(result['organization'], org,
                              'name')
        expected_dict = {
            u'approval_status': u'approved',
            u'description': u'Just another test organization.',
            u'image_url': u'http://placekitten.com/g/200/100',
            u'is_organization': True,
            u'name': u'test_package_dictize',
            u'state': u'active',
            u'title': u'Test Organization',
            u'type': u'organization'
        }
        self.assert_equals_expected(expected_dict, result['organization'])


def assert_equal_for_keys(dict1, dict2, *keys):
    for key in keys:
        assert key in dict1, 'Dict 1 misses key "%s"' % key
        assert key in dict2, 'Dict 2 misses key "%s"' % key
        assert dict1[key] == dict2[key], '%s != %s (key=%s)' % \
            (dict1[key], dict2[key], key)


class TestTagDictize(object):
    """Unit tests for the tag_dictize() function."""

    def test_tag_dictize_including_datasets(self):
        """By default a dictized tag should include the tag's datasets."""
        # Make a dataset in order to have a tag created.
        factories.Dataset(tags=[dict(name="test_tag")])
        tag = model.Tag.get("test_tag")

        tag_dict = model_dictize.tag_dictize(tag, context={"model": model})

        assert len(tag_dict["packages"]) == 1

    def test_tag_dictize_not_including_datasets(self):
        """include_datasets=False should exclude datasets from tag dicts."""
        # Make a dataset in order to have a tag created.
        factories.Dataset(tags=[dict(name="test_tag")])
        tag = model.Tag.get("test_tag")

        tag_dict = model_dictize.tag_dictize(tag, context={"model": model},
                                             include_datasets=False)

        assert not tag_dict.get("packages")


class TestVocabularyDictize(object):
    """Unit tests for the vocabulary_dictize() function."""

    def test_vocabulary_dictize_including_datasets(self):
        """include_datasets=True should include datasets in vocab dicts."""
        vocab_dict = factories.Vocabulary(
            tags=[dict(name="test_tag_1"), dict(name="test_tag_2")])
        factories.Dataset(tags=vocab_dict["tags"])
        vocab_obj = model.Vocabulary.get(vocab_dict["name"])

        vocab_dict = model_dictize.vocabulary_dictize(
            vocab_obj, context={"model": model}, include_datasets=True)

        assert len(vocab_dict["tags"]) == 2
        for tag in vocab_dict["tags"]:
            assert len(tag["packages"]) == 1

    def test_vocabulary_dictize_not_including_datasets(self):
        """By default datasets should not be included in vocab dicts."""
        vocab_dict = factories.Vocabulary(
            tags=[dict(name="test_tag_1"), dict(name="test_tag_2")])
        factories.Dataset(tags=vocab_dict["tags"])
        vocab_obj = model.Vocabulary.get(vocab_dict["name"])

        vocab_dict = model_dictize.vocabulary_dictize(
            vocab_obj, context={"model": model})

        assert len(vocab_dict["tags"]) == 2
        for tag in vocab_dict["tags"]:
            assert len(tag.get("packages", [])) == 0
