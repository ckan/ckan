# encoding: utf-8

from difflib import unified_diff
from pprint import pprint, pformat

from ckan import model

import ckan.lib.search as search
from ckan.lib.dictization.model_save import package_dict_save
from ckan.lib.create_test_data import CreateTestData

from ckan.migration.revision_legacy_code import package_dictize_with_revisions as package_dictize
from ckan.migration.revision_legacy_code import make_package_revision
from ckan.migration.migrate_package_activity import PackageDictizeMonkeyPatch


# tests here have been moved from ckan/tests/legacy/lib/test_dictization.py
class TestPackageDictizeWithRevisions(object):
    @classmethod
    def setup_class(cls):
        # clean the db so we can run these tests on their own
        model.repo.rebuild_db()
        search.clear_all()
        CreateTestData.create()
        make_package_revision(model.Package.by_name('annakarenina'))

        cls.package_expected = {
            u'author': None,
            u'author_email': None,
            u'creator_user_id': None,
            'extras': [
                # extra_revision_table is no longer being populated because
                # PackageExtra no longer has
                # vdm.sqlalchemy.Revisioner(extra_revision_table) (removed in
                # #4691) so don't test extras for the moment
                # {'key': u'david', 'state': u'active', 'value': u'new_value'},
                # {'key': u'genre', 'state': u'active', 'value': u'new_value'},
                # {'key': u'original media', 'state': u'active',
                #  'value': u'book'}
                 ],
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
        make_package_revision(model.Package.by_name('annakarenina_changed'))

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
        anna_dictized['tags'][0].pop('id')  # test if
        anna_dictized['extras'][0]['value'] = u'new_value'

        model.repo.new_revision()
        package_dict_save(anna_dictized, context)
        model.Session.commit()
        model.Session.remove()
        make_package_revision(model.Package.by_name('annakarenina_changed2'))

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
        make_package_revision(model.Package.by_name('annakarenina_changed2'))

    def test_13_get_package_in_past(self):

        context = {'model': model,
                   'session': model.Session}

        anna1 = model.Session.query(model.Package).filter_by(name='annakarenina_changed2').one()

        pkgrevisions = model.Session.query(model.PackageRevision).filter_by(id=anna1.id).all()
        sorted_packages = sorted(pkgrevisions, key=lambda x: x.revision_timestamp)

        context['revision_id'] = sorted_packages[0].revision_id  # original state

        with PackageDictizeMonkeyPatch():
            first_dictized = self.remove_changable_columns(package_dictize(anna1, context))
            assert self.remove_changable_columns(self.package_expected) == first_dictized

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
            second_dictized['state'] = 'active'

            print('\n'.join(unified_diff(pformat(second_dictized).split('\n'), pformat(third_dictized).split('\n'))))
            assert second_dictized == third_dictized

            context['revision_id'] = sorted_packages[3].revision_id  # original state
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
        third_dictized['state'] = 'active'
        third_dictized['state'] = 'active'

        pprint(third_dictized)
        pprint(forth_dictized)

        assert third_dictized == forth_dictized

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

            # TEMPORARY HACK - we remove 'extras' so they aren't tested. This
            # is due to package_extra_revisions being migrated from ckan/model
            # in #4691 but not the rest of the model revisions just yet. Until
            # we finish this work (#4664) it is hard to get this working -
            # extra_revision_table is no longer being populated because
            # PackageExtra no longer has
            # vdm.sqlalchemy.Revisioner(extra_revision_table). However #4664
            # will allow use to manually create revisions and test this again.
            if key == 'extras':
                dict.pop(key)
            # END OF HACK
        return dict
