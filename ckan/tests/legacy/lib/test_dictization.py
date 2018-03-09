# encoding: utf-8

from __future__ import print_function

from nose.tools import assert_equal, assert_not_in, assert_in
from pprint import pprint, pformat
from difflib import unified_diff

import ckan.lib.search as search
from ckan.lib.create_test_data import CreateTestData
from ckan import model
from ckan.lib.dictization import (table_dictize,
                              table_dict_save)

from ckan.lib.dictization.model_dictize import (package_dictize,
                                                resource_dictize,
                                                activity_dictize,
                                                package_to_api1,
                                                package_to_api2,
                                                user_dictize,
                                               )
from ckan.lib.dictization.model_save import (package_dict_save,
                                             resource_dict_save,
                                             group_dict_save,
                                             activity_dict_save,
                                             package_api_to_dict,
                                             group_api_to_dict,
                                             package_tag_list_save,
                                            )
import ckan.logic.action.get


class TestBasicDictize:
    @classmethod
    def setup_class(cls):
        # clean the db so we can run these tests on their own
        model.repo.rebuild_db()
        search.clear_all()
        CreateTestData.create()

        cls.package_expected = {
            u'author': None,
            u'author_email': None,
            u'creator_user_id': None,
            'extras': [
               {u'key': u'genre',
                u'state': u'active',
                u'value': 'romantic novel'},
               {u'key': u'original media', u'state': u'active', u'value': u'book'}],
            'groups': [{
                        u'name': u'david',
                        u'capacity': u'public',
                        u'image_url': u'',
                        u'image_display_url': u'',
                        u'description': u'These are books that David likes.',
                        u'display_name': u"Dave's books",
                        u'type': u'group',
                        u'state': u'active',
                        u'is_organization': False,
                        u'title': u"Dave's books",
                        u"approval_status": u"approved"},
                       {
                        u'name': u'roger',
                        u'capacity': u'public',
                        u'description': u'Roger likes these books.',
                        u'image_url': u'',
                        'image_display_url': u'',
                        'display_name': u"Roger's books",
                        u'type': u'group',
                        u'state': u'active',
                        u'is_organization': False,
                        u'title': u"Roger's books",
                        u"approval_status": u"approved"}],
            'isopen': True,
            u'license_id': u'other-open',
            'license_title': u'Other (Open)',
            'organization': None,
            u'owner_org': None,
            u'maintainer': None,
            u'maintainer_email': None,
            u'name': u'annakarenina',
            u'notes': u'Some test notes\n\n### A 3rd level heading\n\n**Some bolded text.**\n\n*Some italicized text.*\n\nForeign characters:\nu with umlaut \xfc\n66-style quote \u201c\nforeign word: th\xfcmb\n\nNeeds escaping:\nleft arrow <\n\n<http://ckan.net/>\n\n',
            'num_resources': 2,
            'num_tags': 3,
            u'private': False,
            'relationships_as_object': [],
            'relationships_as_subject': [],
            'resources': [{u'alt_url': u'alt123',
                            u'cache_last_updated': None,
                            u'cache_url': None,
                            u'description': u'Full text. Needs escaping: " Umlaut: \xfc',
                            u'format': u'plain text',
                            u'hash': u'abc123',
                            u'last_modified': None,
                            u'mimetype': None,
                            u'mimetype_inner': None,
                            u'name': None,
                            u'position': 0,
                            u'resource_type': None,
                            u'size': None,
                            u'size_extra': u'123',
                            u'url_type': None,
                            u'state': u'active',
                            u'url': u'http://datahub.io/download/x=1&y=2',},
                           {u'alt_url': u'alt345',
                            u'cache_last_updated': None,
                            u'cache_url': None,
                            u'description': u'Index of the novel',
                            u'format': u'JSON',
                            u'hash': u'def456',
                            u'last_modified': None,
                            u'mimetype': None,
                            u'mimetype_inner': None,
                            u'name': None,
                            u'position': 1,
                            u'resource_type': None,
                            u'url_type': None,
                            u'size': None,
                            u'size_extra': u'345',
                            u'state': u'active',
                            u'url': u'http://datahub.io/index.json'}],
            u'state': u'active',
            'tags': [{u'name': u'Flexible \u30a1',
                        'display_name': u'Flexible \u30a1',
                        u'state': u'active'},
                     {'display_name': u'russian',
                         u'name': u'russian',
                         u'state': u'active'},
                     {'display_name': u'tolstoy',
                         u'name': u'tolstoy',
                         u'state': u'active'}],
            u'title': u'A Novel By Tolstoy',
            u'type': u'dataset',
            u'url': u'http://datahub.io',
            u'version': u'0.7a',
            }


    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()
        model.Session.remove()

    def remove_changable_columns(self, dict, remove_package_id=False):
        ids_to_keep = ['license_id', 'creator_user_id']
        if not remove_package_id:
            ids_to_keep.append('package_id')

        for key, value in dict.items():
            if key.endswith('id') and key not in ids_to_keep:
                dict.pop(key)
            if key == 'created':
                dict.pop(key)
            if 'timestamp' in key:
                dict.pop(key)
            if key in ['metadata_created','metadata_modified']:
                dict.pop(key)
            if isinstance(value, list):
                for new_dict in value:
                    self.remove_changable_columns(new_dict,
                        key in ['resources', 'extras'] or remove_package_id)
        return dict

    def remove_revision_id(self, dict):
        for key, value in dict.items():
            if key in ('revision_id', 'revision_timestamp',
                       'expired_timestamp', 'expired_id'):
                dict.pop(key)
            if isinstance(value, list):
                for new_dict in value:
                    self.remove_revision_id(new_dict)
        return dict

    def test_03_package_to_api1(self):

        context = {"model": model,
                 "session": model.Session}

        pkg = model.Session.query(model.Package).filter_by(name='annakarenina').first()

        pprint(package_to_api1(pkg, context))
        pprint(pkg.as_dict())
        asdict = pkg.as_dict()
        asdict['download_url'] = asdict['resources'][0]['url']
        asdict['license_title'] = u'Other (Open)'
        asdict['num_tags'] = 3
        asdict['num_resources'] = 2

        dictize = package_to_api1(pkg, context)
        # the is_dict method doesn't care about organizations
        del dictize['organization']
        assert dictize == asdict

    def test_04_package_to_api1_with_relationship(self):

        context = {"model": model,
                 "session": model.Session}

        create = CreateTestData

        create.create_family_test_data()
        pkg = model.Session.query(model.Package).filter_by(name='homer').one()

        as_dict = pkg.as_dict()
        as_dict['license_title'] = None
        as_dict['num_tags'] = 0
        as_dict['num_resources'] = 0
        dictize = package_to_api1(pkg, context)

        as_dict["relationships"].sort(key=lambda x:x.items())
        dictize["relationships"].sort(key=lambda x:x.items())

        # the is_dict method doesn't care about organizations
        del dictize['organization']
        as_dict_string = pformat(as_dict)
        dictize_string = pformat(dictize)
        print(as_dict_string)
        print(dictize_string)

        assert as_dict == dictize, "\n".join(unified_diff(as_dict_string.split("\n"), dictize_string.split("\n")))

    def test_05_package_to_api2(self):

        context = {"model": model,
                 "session": model.Session}

        pkg = model.Session.query(model.Package).filter_by(name='annakarenina').first()

        as_dict = pkg.as_dict(ref_package_by='id', ref_group_by='id')
        dictize = package_to_api2(pkg, context)

        as_dict_string = pformat(as_dict)
        dictize_string = pformat(dictize)
        print(as_dict_string)
        print(dictize_string)

        assert package_to_api2(pkg, context) == dictize, "\n".join(unified_diff(as_dict_string.split("\n"), dictize_string.split("\n")))

    def test_06_package_to_api2_with_relationship(self):

        context = {"model": model,
                 "session": model.Session}

        pkg = model.Session.query(model.Package).filter_by(name='homer').one()

        as_dict = pkg.as_dict(ref_package_by='id', ref_group_by='id')
        as_dict['license_title'] = None
        as_dict['num_tags'] = 0
        as_dict['num_resources'] = 0
        dictize = package_to_api2(pkg, context)

        as_dict["relationships"].sort(key=lambda x:x.items())
        dictize["relationships"].sort(key=lambda x:x.items())

        # the is_dict method doesn't care about organizations
        del dictize['organization']
        as_dict_string = pformat(as_dict)
        dictize_string = pformat(dictize)
        print(as_dict_string)
        print(dictize_string)

        assert as_dict == dictize, "\n".join(unified_diff(as_dict_string.split("\n"), dictize_string.split("\n")))

    def test_07_table_simple_save(self):

        context = {"model": model,
                 "session": model.Session}

        anna1 = model.Session.query(model.Package).filter_by(name='annakarenina').one()

        anna_dictized = self.remove_changable_columns(table_dictize(anna1, context))

        anna_dictized["name"] = 'annakarenina2'

        model.repo.new_revision()
        table_dict_save(anna_dictized, model.Package, context)
        model.Session.commit()

        pkg = model.Session.query(model.Package).filter_by(name='annakarenina2').one()

        assert self.remove_changable_columns(table_dictize(pkg, context)) == anna_dictized, self.remove_changable_columns(table_dictize(pkg, context))

    def test_08_package_save(self):

        context = {"model": model,
                   "user": 'testsysadmin',
                   "session": model.Session}

        anna1 = model.Session.query(model.Package).filter_by(name='annakarenina').one()

        anna_dictized = self.remove_changable_columns(package_dictize(anna1, context))

        anna_dictized["name"] = u'annakarenina3'

        model.repo.new_revision()
        package_dict_save(anna_dictized, context)
        model.Session.commit()

        # Re-clean anna_dictized
        anna_dictized =  self.remove_changable_columns(anna_dictized)

        pkg = model.Session.query(model.Package).filter_by(name='annakarenina3').one()

        package_dictized = self.remove_changable_columns(package_dictize(pkg, context))

        anna_original = pformat(anna_dictized)
        anna_after_save = pformat(package_dictized)

        assert package_dictized == anna_dictized,\
            "\n".join(unified_diff(anna_original.split("\n"), anna_after_save.split("\n")))

    def test_09_package_alter(self):

        context = {"model": model,
                   "session": model.Session,
                   "user": 'testsysadmin'
                   }

        anna1 = model.Session.query(model.Package).filter_by(name='annakarenina').one()

        anna_dictized = package_dictize(anna1, context)

        anna_dictized["name"] = u'annakarenina_changed'
        anna_dictized["resources"][0]["url"] = u'http://new_url'

        model.repo.new_revision()

        package_dict_save(anna_dictized, context)
        model.Session.commit()
        model.Session.remove()

        pkg = model.Session.query(model.Package).filter_by(name='annakarenina_changed').one()

        package_dictized = package_dictize(pkg, context)

        resources_revisions = model.Session.query(model.ResourceRevision).filter_by(package_id=anna1.id).all()

        sorted_resource_revisions = sorted(resources_revisions, key=lambda x: (x.revision_timestamp, x.url))[::-1]
        for res in sorted_resource_revisions:
            print(res.id, res.revision_timestamp, res.state)
        assert len(sorted_resource_revisions) == 3

        # Make sure we remove changeable fields BEFORE we store the pretty-printed version
        # for comparison
        clean_package_dictized = self.remove_changable_columns(package_dictized)

        anna_original = pformat(anna_dictized)
        anna_after_save = pformat(clean_package_dictized)

        assert self.remove_changable_columns(anna_dictized) == clean_package_dictized, \
            "\n".join(unified_diff(anna_original.split("\n"), anna_after_save.split("\n")))

        # changes to the package, relied upon by later tests
        anna1 = model.Session.query(model.Package).filter_by(name='annakarenina_changed').one()
        anna_dictized = package_dictize(anna1, context)
        anna_dictized['name'] = u'annakarenina_changed2'
        anna_dictized['resources'][0]['url'] = u'http://new_url2'
        anna_dictized['tags'][0]['name'] = u'new_tag'
        anna_dictized['tags'][0].pop('id') #test if
        anna_dictized['extras'][0]['value'] = u'new_value'

        model.repo.new_revision()
        package_dict_save(anna_dictized, context)
        model.Session.commit()
        model.Session.remove()

        anna1 = model.Session.query(model.Package).filter_by(name='annakarenina_changed2').one()
        anna_dictized = package_dictize(anna1, context)
        anna_dictized['notes'] = 'wee'
        anna_dictized['resources'].append({
                            'format': u'plain text',
                            'url': u'http://newurl'}
                            )
        anna_dictized['tags'].append({'name': u'newnew_tag'})
        anna_dictized['extras'].append({'key': 'david',
                                        'value': u'new_value'})

        model.repo.new_revision()
        package_dict_save(anna_dictized, context)
        model.Session.commit()
        model.Session.remove()


    def test_13_get_package_in_past(self):

        context = {'model': model,
                   'session': model.Session}

        anna1 = model.Session.query(model.Package).filter_by(name='annakarenina_changed2').one()

        pkgrevisions = model.Session.query(model.PackageRevision).filter_by(id=anna1.id).all()
        sorted_packages = sorted(pkgrevisions, key=lambda x:x.revision_timestamp)

        context['revision_id'] = sorted_packages[0].revision_id #original state

        first_dictized = self.remove_changable_columns(package_dictize(anna1, context))
        assert self.package_expected == first_dictized

        context['revision_id'] = sorted_packages[1].revision_id

        second_dictized = self.remove_changable_columns(package_dictize(anna1, context))

        first_dictized["name"] = u'annakarenina_changed'
        first_dictized["resources"][0]["url"] = u'http://new_url'

        assert second_dictized == first_dictized

        context['revision_id'] = sorted_packages[2].revision_id
        third_dictized = self.remove_changable_columns(package_dictize(anna1, context))

        second_dictized['name'] = u'annakarenina_changed2'
        second_dictized['resources'][0]['url'] = u'http://new_url2'
        second_dictized['tags'][0]['name'] = u'new_tag'
        second_dictized['tags'][0]['display_name'] = u'new_tag'
        second_dictized['extras'][0]['value'] = u'new_value'
        second_dictized['state'] = 'active'

        print('\n'.join(unified_diff(pformat(second_dictized).split('\n'), pformat(third_dictized).split('\n'))))
        assert second_dictized == third_dictized

        context['revision_id'] = sorted_packages[3].revision_id #original state
        forth_dictized = self.remove_changable_columns(package_dictize(anna1, context))

        third_dictized['notes'] = 'wee'
        third_dictized['resources'].insert(2, {
            u'cache_last_updated': None,
            u'cache_url': None,
            u'description': u'',
            u'format': u'plain text',
            u'hash': u'',
            u'last_modified': None,
            u'mimetype': None,
            u'mimetype_inner': None,
            u'name': None,
            u'position': 2,
            u'resource_type': None,
            u'url_type': None,
            u'size': None,
            u'state': u'active',
            u'url': u'http://newurl'})
        third_dictized['num_resources'] = third_dictized['num_resources'] + 1

        third_dictized['tags'].insert(1, {'name': u'newnew_tag', 'display_name': u'newnew_tag', 'state': 'active'})
        third_dictized['num_tags'] = third_dictized['num_tags'] + 1
        third_dictized['extras'].insert(0, {'key': 'david',
                                         'value': u'new_value',
                                         'state': u'active'})
        third_dictized['state'] = 'active'
        third_dictized['state'] = 'active'

        pprint(third_dictized)
        pprint(forth_dictized)

        assert third_dictized == forth_dictized

    def test_14_resource_no_id(self):

        context = {"model": model,
                 "session": model.Session}

        model.repo.new_revision()
        model.Session.commit()

        new_resource = {
            'mimetype': None,
            u'alt_url': u'empty resource group id',
            'hash': u'abc123',
            'description': u'Full text. Needs escaping: " Umlaut: \xfc',
            'format': u'plain text',
            'url': u'http://test_new',
            'cache_url': None,
            'cache_last_updated': None,
            'state': u'active',
            'mimetype_inner': None,
            'url_type': None,
            'last_modified': None,
            'position': 0,
            'size': None,
            'size_extra': u'123',
            'resource_type': None,
            'name': None,
            'package_id':''  # Just so we can save
        }

        model.repo.new_revision()
        resource_dict_save(new_resource, context)
        model.Session.commit()
        model.Session.remove()

        # Remove the package id
        del new_resource['package_id']

        res = model.Session.query(model.Resource).filter_by(url=u'http://test_new').one()

        res_dictized = self.remove_changable_columns(resource_dictize(res, context), True)

        assert res_dictized == new_resource, res_dictized

    def test_15_api_to_dictize(self):

        context = {"model": model,
                   'api_version': 1,
                 "session": model.Session}

        api_data = {
            'name' : u'testpkg',
            'title': u'Some Title',
            'url': u'http://blahblahblah.mydomain',
            'resources': [ {
                u'url':u'http://blah.com/file2.xml',
                u'format':u'xml',
                u'description':u'Second file',
                u'hash':u'def123',
                u'alt_url':u'alt_url',
                u'size':u'200',
            },
                {
                u'url':u'http://blah.com/file.xml',
                u'format':u'xml',
                u'description':u'Main file',
                u'hash':u'abc123',
                u'alt_url':u'alt_url',
                u'size':u'200',
            },
            ],
            'tags': u'russion novel',
            'license_id': u'gpl-3.0',
            'extras': {
                'genre' : u'horror',
                'media' : u'dvd',
            },
        }

        dictized = package_api_to_dict(api_data, context)

        assert dictized == {'extras': [{'key': 'genre', 'value': u'horror'},
                                       {'key': 'media', 'value': u'dvd'}],
                            'license_id': u'gpl-3.0',
                            'name': u'testpkg',
                            'resources': [{u'alt_url': u'alt_url',
                                          u'description': u'Second file',
                                          u'size': u'200',
                                          u'format': u'xml',
                                          u'hash': u'def123',
                                          u'url': u'http://blah.com/file2.xml'},
                                          {u'alt_url': u'alt_url',
                                          u'description': u'Main file',
                                          u'size': u'200',
                                          u'format': u'xml',
                                          u'hash': u'abc123',
                                          u'url': u'http://blah.com/file.xml'}],
                            'tags': [{'name': u'russion'}, {'name': u'novel'}],
                            'title': u'Some Title',
                            'url': u'http://blahblahblah.mydomain'}

        model.repo.new_revision()

        package_dict_save(dictized, context)
        model.Session.commit()
        model.Session.remove()

        pkg = model.Session.query(model.Package).filter_by(name=u'testpkg').one()

        package_dictized = self.remove_changable_columns(package_dictize(pkg, context))



    def test_17_group_apis_to_dict(self):

        context = {"model": model,
                  "session": model.Session}

        api_group = {
            'name' : u'testgroup',
            'title' : u'Some Group Title',
            'description' : u'Great group!',
            'packages' : [u'annakarenina', u'warandpeace'],
        }


        assert group_api_to_dict(api_group, context) == {'description': u'Great group!',
                                                         'name': u'testgroup',
                                                         'packages': [{'id': u'annakarenina'}, {'id': u'warandpeace'}],
                                                         'title': u'Some Group Title'}, pformat(group_api_to_dict(api_group, context))

    def test_18_package_tag_list_save(self):
        name = u'testpkg18'
        context = {'model': model,
                   'session': model.Session}
        pkg_dict = {'name': name}

        rev = model.repo.new_revision()
        package = table_dict_save(pkg_dict, model.Package, context)

        tag_dicts = [{'name': 'tag1'}, {'name': 'tag2'}]
        package_tag_list_save(tag_dicts, package, context)
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(name)
        assert_equal(set([tag.name for tag in pkg.get_tags()]),
                set(('tag1', 'tag2')))

    def test_19_package_tag_list_save_duplicates(self):
        name = u'testpkg19'
        context = {'model': model,
                   'session': model.Session}
        pkg_dict = {'name': name}

        rev = model.repo.new_revision()
        package = table_dict_save(pkg_dict, model.Package, context)

        tag_dicts = [{'name': 'tag1'}, {'name': 'tag1'}] # duplicate
        package_tag_list_save(tag_dicts, package, context)
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(name)
        assert_equal(set([tag.name for tag in pkg.get_tags()]), set(('tag1',)))

    def test_20_activity_save(self):

        # Add a new Activity object to the database by passing a dict to
        # activity_dict_save()
        context = {"model": model, "session": model.Session}
        user = model.User.by_name(u'tester')
        revision = model.repo.new_revision()
        sent = {
                'user_id': user.id,
                'object_id': user.id,
                'revision_id': revision.id,
                'activity_type': 'changed user'
                }
        activity_dict_save(sent, context)
        model.Session.commit()

        # Retrieve the newest Activity object from the database, check that its
        # attributes match those of the dict we saved.
        got = ckan.logic.action.get.user_activity_list(context,
                {'id': user.id})[0]
        assert got['user_id'] == sent['user_id']
        assert got['object_id'] == sent['object_id']
        assert got['revision_id'] == sent['revision_id']
        assert got['activity_type'] == sent['activity_type']

        # The activity object should also have an ID and timestamp.
        assert got['id']
        assert got['timestamp']

        # We didn't pass in any data so this should be empty.
        assert not got['data']


    def test_21_package_dictization_with_deleted_group(self):
        """
        Ensure that the dictization does not return groups that the dataset has
        been removed from.
        """
        # Create a new dataset and 2 new groups
        model.repo.new_revision()
        pkg = model.Package(name='testing-deleted-groups')
        group_1 = model.Group(name='test-group-1')
        group_2 = model.Group(name='test-group-2')
        model.Session.add(pkg)
        model.Session.add(group_1)
        model.Session.add(group_2)
        model.Session.flush()

        # Add the dataset to group_1, and signal that the dataset used
        # to be a member of group_2 by setting its membership state to 'deleted'
        membership_1 = model.Member(table_id = pkg.id,
                                    table_name = 'package',
                                    group = group_1,
                                    group_id = group_1.id,
                                    state = 'active')

        membership_2 = model.Member(table_id = pkg.id,
                                    table_name = 'package',
                                    group = group_2,
                                    group_id = group_2.id,
                                    state = 'deleted')

        model.Session.add(membership_1)
        model.Session.add(membership_2)
        model.repo.commit()

        # Dictize the dataset
        context = {"model": model,
                   "session": model.Session}

        result = package_dictize(pkg, context)
        self.remove_changable_columns(result)
        assert_not_in('test-group-2', [ g['name'] for g in result['groups'] ])
        assert_in('test-group-1', [ g['name'] for g in result['groups'] ])

    def test_22_user_dictize_as_sysadmin(self):
        '''Sysadmins should be allowed to see certain sensitive data.'''
        context = {
            'model': model,
            'session': model.Session,
            'user': 'testsysadmin',
        }

        user = model.User.by_name('tester')

        user_dict = user_dictize(user, context)

        # Check some of the non-sensitive data
        assert 'name' in user_dict
        assert 'about' in user_dict

        # Check sensitive data is available
        assert 'apikey' in user_dict
        assert 'email' in user_dict

        # Passwords and reset keys should never be available
        assert 'password' not in user_dict
        assert 'reset_key' not in user_dict

    def test_23_user_dictize_as_same_user(self):
        '''User should be able to see their own sensitive data.'''
        context = {
            'model': model,
            'session': model.Session,
            'user': 'tester',
        }

        user = model.User.by_name('tester')

        user_dict = user_dictize(user, context)

        # Check some of the non-sensitive data
        assert 'name' in user_dict
        assert 'about' in user_dict

        # Check sensitive data is available
        assert 'apikey' in user_dict
        assert 'email' in user_dict

        # Passwords and reset keys should never be available
        assert 'password' not in user_dict
        assert 'reset_key' not in user_dict

    def test_24_user_dictize_as_other_user(self):
        '''User should not be able to see other's sensitive data.'''
        context = {
            'model': model,
            'session': model.Session,
            'user': 'annafan',
        }

        user = model.User.by_name('tester')

        user_dict = user_dictize(user, context)

        # Check some of the non-sensitive data
        assert 'name' in user_dict
        assert 'about' in user_dict

        # Check sensitive data is not available
        assert 'apikey' not in user_dict
        assert 'reset_key' not in user_dict
        assert 'email' not in user_dict

        # Passwords should never be available
        assert 'password' not in user_dict

    def test_25_user_dictize_as_anonymous(self):
        '''Anonymous should not be able to see other's sensitive data.'''
        context = {
            'model': model,
            'session': model.Session,
            'user': '',
        }

        user = model.User.by_name('tester')

        user_dict = user_dictize(user, context)

        # Check some of the non-sensitive data
        assert 'name' in user_dict
        assert 'about' in user_dict

        # Check sensitive data is not available
        assert 'apikey' not in user_dict
        assert 'reset_key' not in user_dict
        assert 'email' not in user_dict

        # Passwords should never be available
        assert 'password' not in user_dict
