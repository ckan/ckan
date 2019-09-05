# encoding: utf-8

import copy

from nose.tools import assert_equal as eq

from ckan.lib.changes import check_metadata_changes, check_resource_changes
from ckan.tests import helpers
from ckan.tests.factories import Dataset, Organization, Group


def _new_pkg(new):
    return {
        u'pkg_id': new['id'],
        u'name': new['name'],
        u'title': new['title']
    }


class TestCheckMetadataChanges(object):

    def setup(self):
        helpers.reset_db()

    def test_title(self):
        changes = []
        original = Dataset()
        new = helpers.call_action(u'package_patch', id=original['id'],
                                  title=u'New title')

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        eq(changes[0]['type'], u'title')
        eq(changes[0]['old_title'], u'Test Dataset')
        eq(changes[0]['new_title'], u'New title')

    def test_name(self):
        changes = []
        original = Dataset()
        new = helpers.call_action(u'package_patch', id=original['id'],
                                  name=u'new-name')

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        eq(changes[0]['type'], u'name')
        eq(changes[0]['old_name'], original['name'])
        eq(changes[0]['new_name'], u'new-name')

    def test_add_extra(self):
        changes = []
        original = Dataset()
        new = helpers.call_action(
            u'package_patch', id=original['id'],
            extras=[{u'key': u'subject', u'value': u'science'}])

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        eq(changes[0]['type'], u'extra_fields')
        eq(changes[0]['method'], u'add_one_value')
        eq(changes[0]['key'], u'subject')
        eq(changes[0]['value'], u'science')

    # TODO how to test 'add_one_no_value'?

    def test_add_multiple_extras(self):
        changes = []
        original = Dataset()
        new = helpers.call_action(
            u'package_patch', id=original['id'],
            extras=[{u'key': u'subject', u'value': u'science'},
                    {u'key': u'topic', u'value': u'wind'}])

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        eq(changes[0]['type'], u'extra_fields')
        eq(changes[0]['method'], u'add_multiple')
        eq(set(changes[0]['key_list']), set([u'subject', u'topic']))

    def test_change_extra(self):
        changes = []
        original = Dataset(
            extras=[{u'key': u'subject', u'value': u'science'},
                    {u'key': u'topic', u'value': u'wind'}])
        new = helpers.call_action(
            u'package_patch', id=original['id'],
            extras=[{u'key': u'subject', u'value': u'scientific'},
                    {u'key': u'topic', u'value': u'wind'}])

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        eq(changes[0]['type'], u'extra_fields')
        eq(changes[0]['method'], u'change_with_old_value')
        eq(changes[0]['key'], u'subject')
        eq(changes[0]['old_value'], u'science')
        eq(changes[0]['new_value'], u'scientific')

    def test_change_multiple_extras(self):
        changes = []
        original = Dataset(
            extras=[{u'key': u'subject', u'value': u'science'},
                    {u'key': u'topic', u'value': u'wind'}])
        new = helpers.call_action(
            u'package_patch', id=original['id'],
            extras=[{u'key': u'subject', u'value': u'scientific'},
                    {u'key': u'topic', u'value': u'rain'}])

        check_metadata_changes(changes, original, new)

        assert len(changes) == 2, changes
        for change in changes:
            eq(change['type'], u'extra_fields')
            eq(change['method'], u'change_with_old_value')
            if change['key'] == u'subject':
                eq(change['new_value'], u'scientific')
            else:
                eq(changes[0]['key'], u'topic')
                eq(change['new_value'], u'rain')

    # TODO how to test change2?

    def test_delete_extra(self):
        changes = []
        original = Dataset(
            extras=[{u'key': u'subject', u'value': u'science'},
                    {u'key': u'topic', u'value': u'wind'}])
        new = helpers.call_action(
            u'package_patch', id=original['id'],
            extras=[{u'key': u'topic', u'value': u'wind'}])

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        eq(changes[0]['type'], u'extra_fields')
        eq(changes[0]['method'], u'remove_one')
        eq(changes[0]['key'], u'subject')

    def test_delete_multiple_extras(self):
        changes = []
        original = Dataset(
            extras=[{u'key': u'subject', u'value': u'science'},
                    {u'key': u'topic', u'value': u'wind'},
                    {u'key': u'geography', u'value': u'global'}])
        new = helpers.call_action(
            u'package_patch', id=original['id'],
            extras=[{u'key': u'topic', u'value': u'wind'}])

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        eq(changes[0]['type'], u'extra_fields')
        eq(changes[0]['method'], u'remove_multiple')
        eq(set(changes[0]['key_list']), set((u'subject', u'geography')))

    def test_add_maintainer(self):
        changes = []
        original = Dataset()
        new = helpers.call_action(
            u'package_patch', id=original['id'],
            maintainer=u'new maintainer')

        check_metadata_changes(changes, original, new)

        eq(changes[0]['type'], u'maintainer')
        eq(changes[0]['method'], u'add')
        eq(changes[0]['new_maintainer'], u'new maintainer')

    def test_change_maintainer(self):
        changes = []
        original = Dataset(maintainer=u'first maintainer')
        new = helpers.call_action(
            u'package_patch', id=original['id'],
            maintainer=u'new maintainer')

        check_metadata_changes(changes, original, new)

        eq(changes[0]['type'], u'maintainer')
        eq(changes[0]['method'], u'change')
        eq(changes[0]['old_maintainer'], u'first maintainer')
        eq(changes[0]['new_maintainer'], u'new maintainer')

    def test_remove_maintainer(self):
        changes = []
        original = Dataset(maintainer=u'first maintainer')
        new = helpers.call_action(
            u'package_patch', id=original['id'],
            maintainer=u'')

        check_metadata_changes(changes, original, new)

        eq(changes[0]['type'], u'maintainer')
        eq(changes[0]['method'], u'remove')

    def test_add_notes(self):
        changes = []
        original = Dataset(notes=u'')
        new = helpers.call_action(
            u'package_patch', id=original['id'],
            notes=u'new notes')

        check_metadata_changes(changes, original, new)

        eq(changes[0]['type'], u'notes')
        eq(changes[0]['method'], u'add')
        eq(changes[0]['new_notes'], u'new notes')

    def test_change_notes(self):
        changes = []
        original = Dataset(notes=u'first notes')
        new = helpers.call_action(
            u'package_patch', id=original['id'],
            notes=u'new notes')

        check_metadata_changes(changes, original, new)

        eq(changes[0]['type'], u'notes')
        eq(changes[0]['method'], u'change')
        eq(changes[0]['old_notes'], u'first notes')
        eq(changes[0]['new_notes'], u'new notes')

    def test_remove_notes(self):
        changes = []
        original = Dataset(notes=u'first notes')
        new = helpers.call_action(
            u'package_patch', id=original['id'],
            notes=u'')

        check_metadata_changes(changes, original, new)

        eq(changes[0]['type'], u'notes')
        eq(changes[0]['method'], u'remove')

    @helpers.change_config(u'ckan.auth.create_unowned_dataset', True)
    def test_add_org(self):
        changes = []
        original = Dataset(owner_org=None)
        new_org = Organization()
        new = helpers.call_action(
            u'package_patch', id=original['id'],
            owner_org=new_org['id'])

        check_metadata_changes(changes, original, new)

        eq(changes[0]['type'], u'org')
        eq(changes[0]['method'], u'add')
        eq(changes[0]['new_org_id'], new_org['id'])

    def test_change_org(self):
        changes = []
        old_org = Organization()
        original = Dataset(owner_org=old_org['id'])
        new_org = Organization()
        new = helpers.call_action(
            u'package_patch', id=original['id'],
            owner_org=new_org['id'])

        check_metadata_changes(changes, original, new)

        eq(changes[0]['type'], u'org')
        eq(changes[0]['method'], u'change')
        eq(changes[0]['old_org_id'], original['organization']['id'])
        eq(changes[0]['new_org_id'], new_org['id'])

    @helpers.change_config(u'ckan.auth.create_unowned_dataset', True)
    def test_remove_org(self):
        changes = []
        old_org = Organization()
        original = Dataset(owner_org=old_org['id'])

        import ckan.model as model
        pkg = model.Package.get(original['id'])
        pkg.owner_org = None
        pkg.save()

        new = helpers.call_action(
            u'package_show', id=original['id'])

        check_metadata_changes(changes, original, new)

        eq(changes[0]['type'], u'org')
        eq(changes[0]['method'], u'remove')

    def test_make_private(self):
        changes = []
        old_org = Organization()
        original = Dataset(owner_org=old_org['id'], private=False)
        new = helpers.call_action(u'package_patch', id=original['id'],
                                  private=True)

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        eq(changes[0]['type'], u'private')
        eq(changes[0]['new'], u'Private')

    def test_make_public(self):
        changes = []
        old_org = Organization()
        original = Dataset(owner_org=old_org['id'], private=True)
        new = helpers.call_action(u'package_patch', id=original['id'],
                                  private=False)

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        eq(changes[0]['type'], u'private')
        eq(changes[0]['new'], u'Public')

    def test_add_tag(self):
        changes = []
        original = Dataset(tags=[{u'name': u'rivers'}])
        new = helpers.call_action(u'package_patch', id=original['id'],
                                  tags=[{u'name': u'rivers'},
                                        {u'name': u'oceans'}])

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        eq(changes[0]['type'], u'tags')
        eq(changes[0]['method'], u'add_one')
        eq(changes[0]['tag'], u'oceans')

    def test_add_multiple_tags(self):
        changes = []
        original = Dataset(tags=[{u'name': u'rivers'}])
        new = helpers.call_action(u'package_patch', id=original['id'],
                                  tags=[{u'name': u'rivers'},
                                        {u'name': u'oceans'},
                                        {u'name': u'streams'}])

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        eq(changes[0]['type'], u'tags')
        eq(changes[0]['method'], u'add_multiple')
        eq(set(changes[0]['tags']), set((u'oceans', u'streams')))

    def test_delete_tag(self):
        changes = []
        original = Dataset(tags=[{u'name': u'rivers'},
                                 {u'name': u'oceans'}])
        new = helpers.call_action(u'package_patch', id=original['id'],
                                  tags=[{u'name': u'rivers'}])

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        eq(changes[0]['type'], u'tags')
        eq(changes[0]['method'], u'remove_one')
        eq(changes[0]['tag'], u'oceans')

    def test_remove_multiple_tags(self):
        changes = []
        original = Dataset(tags=[{u'name': u'rivers'},
                                 {u'name': u'oceans'},
                                 {u'name': u'streams'}])
        new = helpers.call_action(u'package_patch', id=original['id'],
                                  tags=[{u'name': u'rivers'}])

        check_metadata_changes(changes, original, new)

        assert len(changes) == 1, changes
        eq(changes[0]['type'], u'tags')
        eq(changes[0]['method'], u'remove_multiple')
        eq(set(changes[0]['tags']), set((u'oceans', u'streams')))

    def test_add_url(self):
        changes = []
        original = Dataset()
        new = helpers.call_action(
            u'package_patch', id=original['id'],
            url=u'new url')

        check_metadata_changes(changes, original, new)

        eq(changes[0]['type'], u'url')
        eq(changes[0]['method'], u'add')
        eq(changes[0]['new_url'], u'new url')

    def test_change_url(self):
        changes = []
        original = Dataset(url=u'first url')
        new = helpers.call_action(
            u'package_patch', id=original['id'],
            url=u'new url')

        check_metadata_changes(changes, original, new)

        eq(changes[0]['type'], u'url')
        eq(changes[0]['method'], u'change')
        eq(changes[0]['old_url'], u'first url')
        eq(changes[0]['new_url'], u'new url')

    def test_remove_url(self):
        changes = []
        original = Dataset(url=u'first url')
        new = helpers.call_action(
            u'package_patch', id=original['id'],
            url=u'')

        check_metadata_changes(changes, original, new)

        eq(changes[0]['type'], u'url')
        eq(changes[0]['method'], u'remove')

    def test_add_version(self):
        changes = []
        original = Dataset()
        new = helpers.call_action(
            u'package_patch', id=original['id'],
            version=u'new version')

        check_metadata_changes(changes, original, new)

        eq(changes[0]['type'], u'version')
        eq(changes[0]['method'], u'add')
        eq(changes[0]['new_version'], u'new version')

    def test_change_version(self):
        changes = []
        original = Dataset(version=u'first version')
        new = helpers.call_action(
            u'package_patch', id=original['id'],
            version=u'new version')

        check_metadata_changes(changes, original, new)

        eq(changes[0]['type'], u'version')
        eq(changes[0]['method'], u'change')
        eq(changes[0]['old_version'], u'first version')
        eq(changes[0]['new_version'], u'new version')

    def test_remove_version(self):
        changes = []
        original = Dataset(version=u'first version')
        new = helpers.call_action(
            u'package_patch', id=original['id'],
            version=u'')

        check_metadata_changes(changes, original, new)

        eq(changes[0]['type'], u'version')
        eq(changes[0]['method'], u'remove')


class TestCheckResourceChanges(object):

    def setup(self):
        helpers.reset_db()

    def test_add_resource(self):
        changes = []
        original = Dataset()
        new = helpers.call_action(
            u'package_patch', id=original['id'],
            resources=[{u'url': u'http://example.com/image.png',
                        u'format': u'png',
                        u'name': u'Image 1'}])

        check_resource_changes(changes, original, new, u'fake')

        assert len(changes) == 1, changes
        eq(changes[0]['type'], u'new_resource')
        eq(changes[0]['resource_name'], u'Image 1')

    def test_add_multiple_resources(self):
        changes = []
        original = Dataset()
        new = helpers.call_action(
            u'package_patch', id=original['id'],
            resources=[{u'url': u'http://example.com/image.png',
                        u'format': u'png',
                        u'name': u'Image 1'},
                       {u'url': u'http://example.com/image2.png',
                        u'format': u'png',
                        u'name': u'Image 2'}])

        check_resource_changes(changes, original, new, u'fake')

        assert len(changes) == 2, changes
        eq(changes[0]['type'], u'new_resource')
        eq(changes[1]['type'], u'new_resource')
        if changes[0]['resource_name'] == u'Image 1':
            eq(changes[1]['resource_name'], u'Image 2')
        else:
            eq(changes[1]['resource_name'], u'Image 1')
            eq(changes[0]['resource_name'], u'Image 2')

    def test_change_resource_url(self):
        changes = []
        original = Dataset(
            resources=[{u'url': u'http://example.com/image.png',
                        u'format': u'png',
                        u'name': u'Image 1'},
                       {u'url': u'http://example.com/image.png',
                        u'format': u'png',
                        u'name': u'Image 2'}])
        new = copy.deepcopy(original)
        new['resources'][1][u'url'] = u'http://example.com/image_changed.png'
        new = helpers.call_action(u'package_update', **new)

        check_resource_changes(changes, original, new, u'fake')

        assert len(changes) == 1, changes
        eq(changes[0]['type'], u'new_file')
        eq(changes[0]['resource_name'], u'Image 2')

    def test_change_resource_format(self):
        changes = []
        original = Dataset(
            resources=[{u'url': u'http://example.com/image.png',
                        u'format': u'png',
                        u'name': u'Image 1'},
                       {u'url': u'http://example.com/image.png',
                        u'format': u'png',
                        u'name': u'Image 2'}])
        new = copy.deepcopy(original)
        new['resources'][1]['format'] = u'jpg'
        new = helpers.call_action(u'package_update', **new)

        check_resource_changes(changes, original, new, u'fake')

        assert len(changes) == 1, changes
        eq(changes[0]['type'], u'resource_format')
        eq(changes[0]['resource_name'], u'Image 2')

    def test_change_resource_name(self):
        changes = []
        original = Dataset(
            resources=[{u'url': u'http://example.com/image.png',
                        u'format': u'png',
                        u'name': u'Image 1'},
                       {u'url': u'http://example.com/image.png',
                        u'format': u'png',
                        u'name': u'Image 2'}])
        new = copy.deepcopy(original)
        new['resources'][1]['name'] = u'Image changed'
        new = helpers.call_action(u'package_update', **new)

        check_resource_changes(changes, original, new, u'fake')

        assert len(changes) == 1, changes
        eq(changes[0]['type'], u'resource_name')
        eq(changes[0]['old_resource_name'], u'Image 2')
        eq(changes[0]['new_resource_name'], u'Image changed')

    def test_change_resource_description(self):
        changes = []
        original = Dataset(
            resources=[{u'url': u'http://example.com/image.png',
                        u'format': u'png',
                        u'name': u'Image 1',
                        u'description': u'First image'},
                       {u'url': u'http://example.com/image.png',
                        u'format': u'png',
                        u'name': u'Image 2',
                        u'description': u'Second image'}])
        new = copy.deepcopy(original)
        new['resources'][1]['description'] = u'changed'
        new = helpers.call_action(u'package_update', **new)

        check_resource_changes(changes, original, new, u'fake')

        assert len(changes) == 1, changes
        eq(changes[0]['type'], u'resource_desc')
        eq(changes[0]['method'], u'change')
        eq(changes[0]['resource_name'], u'Image 2')

    def test_add_resource_extra(self):
        changes = []
        original = Dataset(
            resources=[{u'url': u'http://example.com/image.png',
                        u'format': u'png',
                        u'name': u'Image 1'}])
        new = copy.deepcopy(original)
        new['resources'][0]['new key'] = u'new value'
        new = helpers.call_action(u'package_update', **new)

        check_resource_changes(changes, original, new, u'fake')

        assert len(changes) == 1, changes
        eq(changes[0]['type'], u'resource_extras')
        eq(changes[0]['method'], u'add_one_value')
        eq(changes[0]['key'], u'new key')
        eq(changes[0]['value'], u'new value')

    def test_change_resource_extra(self):
        changes = []
        original = Dataset(
            resources=[{u'url': u'http://example.com/image.png',
                        u'format': u'png',
                        u'name': u'Image 1',
                        u'key1': u'value1'}])
        new = copy.deepcopy(original)
        new['resources'][0]['key1'] = u'new value'
        new = helpers.call_action(u'package_update', **new)

        check_resource_changes(changes, original, new, u'fake')

        assert len(changes) == 1, changes
        eq(changes[0]['type'], u'resource_extras')
        eq(changes[0]['method'], u'change_value_with_old')
        eq(changes[0]['key'], u'key1')
        eq(changes[0]['old_value'], u'value1')
        eq(changes[0]['new_value'], u'new value')

    def test_remove_resource_extra(self):
        changes = []
        original = Dataset(
            resources=[{u'url': u'http://example.com/image.png',
                        u'format': u'png',
                        u'name': u'Image 1',
                        u'key1': u'value1'}])
        new = copy.deepcopy(original)
        del new['resources'][0]['key1']
        new = helpers.call_action(u'package_update', **new)

        check_resource_changes(changes, original, new, u'fake')

        assert len(changes) == 1, changes
        eq(changes[0]['type'], u'resource_extras')
        eq(changes[0]['method'], u'remove_one')
        eq(changes[0]['key'], u'key1')

    def test_change_multiple_resources(self):
        changes = []
        original = Dataset(
            resources=[{u'url': u'http://example.com/image.png',
                        u'format': u'png',
                        u'name': u'Image 1'},
                       {u'url': u'http://example.com/image.png',
                        u'format': u'png',
                        u'name': u'Image 2'},
                       {u'url': u'http://example.com/image.png',
                        u'format': u'png',
                        u'name': u'Image 3'}])
        new = copy.deepcopy(original)
        new['resources'][0]['name'] = u'changed-1'
        new['resources'][1]['name'] = u'changed-2'
        new = helpers.call_action(u'package_update', **new)

        check_resource_changes(changes, original, new, u'fake')

        assert len(changes) == 2, changes
        eq(changes[0]['type'], u'resource_name')
        eq(changes[1]['type'], u'resource_name')
        if changes[0]['old_resource_name'] == u'Image 1':
            eq(changes[0]['new_resource_name'], u'changed-1')
        else:
            eq(changes[0]['old_resource_name'], u'Image 2')
            eq(changes[0]['new_resource_name'], u'changed-2')

    def test_delete_resource(self):
        changes = []
        original = Dataset(
            resources=[{u'url': u'http://example.com/image.png',
                        u'format': u'png',
                        u'name': u'Image 1'},
                       {u'url': u'http://example.com/image.png',
                        u'format': u'png',
                        u'name': u'Image 2'}])
        new = copy.deepcopy(original)
        del new['resources'][0]
        new = helpers.call_action(u'package_update', **new)

        check_resource_changes(changes, original, new, u'fake')

        assert len(changes) == 1, changes
        eq(changes[0]['type'], u'delete_resource')
        eq(changes[0]['resource_name'], u'Image 1')

    def test_delete_multiple_resources(self):
        changes = []
        original = Dataset(
            resources=[{u'url': u'http://example.com/image.png',
                        u'format': u'png',
                        u'name': u'Image 1'},
                       {u'url': u'http://example.com/image.png',
                        u'format': u'png',
                        u'name': u'Image 2'},
                       {u'url': u'http://example.com/image.png',
                        u'format': u'png',
                        u'name': u'Image 3'}])
        new = copy.deepcopy(original)
        del new['resources'][1]
        del new['resources'][0]
        new = helpers.call_action(u'package_update', **new)

        check_resource_changes(changes, original, new, u'fake')

        assert len(changes) == 2, changes
        eq(changes[0]['type'], u'delete_resource')
        if changes[0]['resource_name'] == u'Image 1':
            eq(changes[1]['resource_name'], u'Image 2')
        else:
            eq(changes[0]['resource_name'], u'Image 2')
            eq(changes[1]['resource_name'], u'Image 1')
