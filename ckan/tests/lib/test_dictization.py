from nose.tools import assert_equal
from pprint import pprint, pformat
from difflib import unified_diff

from ckan.lib.create_test_data import CreateTestData
from ckan import model
from ckan.lib.dictization import (table_dictize,
                              table_dict_save)

from ckan.lib.dictization.model_dictize import (package_dictize,
                                                resource_dictize,
                                                group_dictize,
                                                activity_dictize,
                                                package_to_api1,
                                                package_to_api2,
                                               )
from ckan.lib.dictization.model_save import (package_dict_save,
                                             resource_dict_save,
                                             group_dict_save,
                                             activity_dict_save,
                                             package_api_to_dict,
                                             group_api_to_dict,
                                             package_tag_list_save,
                                            )
from ckan.logic.action.update import make_latest_pending_package_active
import ckan.logic.action.get

class TestBasicDictize:
    @classmethod
    def setup_class(cls):
        CreateTestData.create()

        cls.package_expected = {
            'author': None,
            'author_email': None,
            'extras': [
               {'key': u'genre',
                'state': u'active',
                'value': '"romantic novel"'},
               {'key': u'original media', 'state': u'active', 'value': u'"book"'}],
            'groups': [{'description': u'These are books that David likes.',
                        'name': u'david',
                        'type': u'group',
                        'state': u'active',
                        'title': u"Dave's books"},
                       {'description': u'Roger likes these books.',
                        'name': u'roger',
                        'type': u'group',
                        'state': u'active',
                        'title': u"Roger's books"}],
            'isopen': True,
            'license_id': u'other-open',
            'maintainer': None,
            'maintainer_email': None,
            'type': None,
            'name': u'annakarenina',
            'notes': u'Some test notes\n\n### A 3rd level heading\n\n**Some bolded text.**\n\n*Some italicized text.*\n\nForeign characters:\nu with umlaut \xfc\n66-style quote \u201c\nforeign word: th\xfcmb\n \nNeeds escaping:\nleft arrow <\n\n<http://ckan.net/>\n\n',
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
                            u'state': u'active',
                            u'url': u'http://www.annakarenina.com/download/x=1&y=2',
                            u'webstore_last_updated': None,
                            u'webstore_url': None},
                           {u'alt_url': u'alt345',
                            u'cache_last_updated': None,
                            u'cache_url': None,
                            u'description': u'Index of the novel',
                            u'format': u'json',
                            u'hash': u'def456',
                            u'last_modified': None,
                            u'mimetype': None,
                            u'mimetype_inner': None,
                            u'name': None,
                            u'position': 1,
                            u'resource_type': None,
                            u'size': None,
                            u'size_extra': u'345',
                            u'state': u'active',
                            u'url': u'http://www.annakarenina.com/index.json',
                            u'webstore_last_updated': None,
                            u'webstore_url': None}],
            'state': u'active',
            'tags': [{'name': u'Flexible \u30a1', 'state': u'active'},
                     {'name': u'russian', 'state': u'active'},
                     {'name': u'tolstoy', 'state': u'active'}],
            'title': u'A Novel By Tolstoy',
            'url': u'http://www.annakarenina.com',
            'version': u'0.7a'}
        

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()
        model.Session.remove()

    def remove_changable_columns(self, dict):
        for key, value in dict.items():
            if key.endswith('id') and key <> 'license_id':
                dict.pop(key)
            if key == 'created':
                dict.pop(key)
            if 'timestamp' in key:
                dict.pop(key)
            if key in ['metadata_created','metadata_modified']:
                dict.pop(key)
            if isinstance(value, list):
                for new_dict in value:
                    self.remove_changable_columns(new_dict)
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

    def test_01_dictize_main_objects_simple(self):
        
        context = {"model": model,
                   "session": model.Session}

        ## package
        pkg = model.Session.query(model.Package).filter_by(name='annakarenina').first()
        result = table_dictize(pkg, context)
        self.remove_changable_columns(result)

        assert result == {
            'author': None,
            'author_email': None,
            'license_id': u'other-open',
            'maintainer': None,
            'maintainer_email': None,
            'name': u'annakarenina',
            'type': None,
            'notes': u'Some test notes\n\n### A 3rd level heading\n\n**Some bolded text.**\n\n*Some italicized text.*\n\nForeign characters:\nu with umlaut \xfc\n66-style quote \u201c\nforeign word: th\xfcmb\n \nNeeds escaping:\nleft arrow <\n\n<http://ckan.net/>\n\n',
            'state': u'active',
            'title': u'A Novel By Tolstoy',
            'url': u'http://www.annakarenina.com',
            'version': u'0.7a'
        }, pprint(result)

        ## resource

        resource = pkg.resource_groups[0].resources[0]

        result = resource_dictize(resource, context)
        self.remove_changable_columns(result)


        assert result == {
            u'alt_url': u'alt123',
             'cache_last_updated': None,
             'cache_url': None,
             'description': u'Full text. Needs escaping: " Umlaut: \xfc',
             'format': u'plain text',
             'hash': u'abc123',
             'last_modified': None,
             'mimetype': None,
             'mimetype_inner': None,
             'name': None,
             'position': 0,
             'resource_type': None,
             'size': None,
             u'size_extra': u'123',
             'state': u'active',
             'url': u'http://www.annakarenina.com/download/x=1&y=2',
             'webstore_last_updated': None,
             'webstore_url': None
            }, pprint(result)

        ## package extra

        key, package_extras = pkg._extras.popitem()

        result = table_dictize(package_extras, context)
        self.remove_changable_columns(result)

        assert result == {
            'key': u'genre',
            'state': u'active',
            'value': u'romantic novel'
        }, pprint(result)


    def test_02_package_dictize(self):
        
        context = {"model": model,
                 "session": model.Session}

        model.Session.remove()
        pkg = model.Session.query(model.Package).filter_by(name='annakarenina').first()

        result = package_dictize(pkg, context)
        self.remove_changable_columns(result)

        pprint(result)
        pprint(self.package_expected)

        assert sorted(result.values()) == sorted(self.package_expected.values())
        assert result == self.package_expected



    def test_03_package_to_api1(self):

        context = {"model": model,
                 "session": model.Session}

        pkg = model.Session.query(model.Package).filter_by(name='annakarenina').first()

        pprint(package_to_api1(pkg, context))
        pprint(pkg.as_dict())
        asdict = pkg.as_dict()
        asdict['download_url'] = asdict['resources'][0]['url']

        assert package_to_api1(pkg, context) == asdict

    def test_04_package_to_api1_with_relationship(self):

        context = {"model": model,
                 "session": model.Session}

        create = CreateTestData

        create.create_family_test_data()
        pkg = model.Session.query(model.Package).filter_by(name='homer').one()

        as_dict = pkg.as_dict()
        dictize = package_to_api1(pkg, context)

        as_dict["relationships"].sort(key=lambda x:x.items())
        dictize["relationships"].sort(key=lambda x:x.items())

        as_dict_string = pformat(as_dict)
        dictize_string = pformat(dictize)
        print as_dict_string
        print dictize_string

        assert as_dict == dictize, "\n".join(unified_diff(as_dict_string.split("\n"), dictize_string.split("\n")))

    def test_05_package_to_api2(self):

        context = {"model": model,
                 "session": model.Session}

        pkg = model.Session.query(model.Package).filter_by(name='annakarenina').first()

        as_dict = pkg.as_dict(ref_package_by='id', ref_group_by='id')
        dictize = package_to_api2(pkg, context)

        as_dict_string = pformat(as_dict)
        dictize_string = pformat(dictize)
        print as_dict_string
        print dictize_string

        assert package_to_api2(pkg, context) == dictize, "\n".join(unified_diff(as_dict_string.split("\n"), dictize_string.split("\n")))

    def test_06_package_to_api2_with_relationship(self):

        context = {"model": model,
                 "session": model.Session}

        pkg = model.Session.query(model.Package).filter_by(name='homer').one()

        as_dict = pkg.as_dict(ref_package_by='id', ref_group_by='id')
        dictize = package_to_api2(pkg, context)

        as_dict["relationships"].sort(key=lambda x:x.items())
        dictize["relationships"].sort(key=lambda x:x.items())

        as_dict_string = pformat(as_dict)
        dictize_string = pformat(dictize)
        print as_dict_string
        print dictize_string

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
                   "session": model.Session}

        anna1 = model.Session.query(model.Package).filter_by(name='annakarenina').one()

        

        anna_dictized = self.remove_changable_columns(package_dictize(anna1, context))

        anna_dictized["name"] = u'annakarenina3' 

        model.repo.new_revision()
        package_dict_save(anna_dictized, context)
        model.Session.commit()

        pkg = model.Session.query(model.Package).filter_by(name='annakarenina3').one()

        package_dictized = self.remove_changable_columns(package_dictize(pkg, context))

        anna_original = pformat(anna_dictized)
        anna_after_save = pformat(package_dictized)

        assert self.remove_changable_columns(package_dictize(pkg, context)) == anna_dictized, "\n".join(unified_diff(anna_original.split("\n"), anna_after_save.split("\n")))

    def test_09_package_alter(self):

        context = {"model": model,
                 "session": model.Session}

        anna1 = model.Session.query(model.Package).filter_by(name='annakarenina').one()

        anna_dictized = package_dictize(anna1, context)

        anna_dictized["name"] = u'annakarenina_changed' 
        anna_dictized["resources"][0]["url"] = u'new_url' 

        model.repo.new_revision()
        package_dict_save(anna_dictized, context)
        model.Session.commit()
        model.Session.remove()

        pkg = model.Session.query(model.Package).filter_by(name='annakarenina_changed').one()

        package_dictized = package_dictize(pkg, context)

        resources_revisions = model.Session.query(model.ResourceRevision).filter_by(resource_group_id=anna1.resource_groups[0].id).all()

        sorted_resources = sorted(resources_revisions, key=lambda x: (x.revision_timestamp, x.url))[::-1]
        for res in sorted_resources:
            print res.id, res.revision_timestamp, res.expired_timestamp, res.state, res.current
        assert len(sorted_resources) == 3

        anna_original = pformat(anna_dictized)
        anna_after_save = pformat(package_dictized)

        print anna_original
        print anna_after_save

        assert self.remove_changable_columns(anna_dictized) == self.remove_changable_columns(package_dictized)
        assert "\n".join(unified_diff(anna_original.split("\n"), anna_after_save.split("\n")))

    def test_10_package_alter_pending(self):

        context = {'model': model,
                   'session': model.Session,
                   'pending': True}

        anna1 = model.Session.query(model.Package).filter_by(name='annakarenina_changed').one()

        anna_dictized = package_dictize(anna1, context)

        anna_dictized['name'] = u'annakarenina_changed2' 
        anna_dictized['resources'][0]['url'] = u'new_url2' 
        anna_dictized['tags'][0]['name'] = u'new_tag' 
        anna_dictized['tags'][0].pop('id') #test if 
        anna_dictized['extras'][0]['value'] = u'"new_value"' 

        model.repo.new_revision()
        package_dict_save(anna_dictized, context)
        model.Session.commit()
        model.Session.remove()

        pkgrevisions = model.Session.query(model.PackageRevision).filter_by(id=anna1.id).all()

        sorted_packages = sorted(pkgrevisions, key=lambda x:x.revision_timestamp)[::-1]

        assert len(sorted_packages) == 3
        assert sorted_packages[0].state == 'pending'
        assert sorted_packages[1].state == 'active'
        assert sorted_packages[1].current
        assert sorted_packages[2].state == 'active'

        assert str(sorted_packages[0].expired_timestamp) == '9999-12-31 00:00:00'
        assert str(sorted_packages[1].expired_timestamp) != '9999-12-31 00:00:00'
        assert str(sorted_packages[2].expired_timestamp) != '9999-12-31 00:00:00'

        resources_revisions = model.Session.query(model.ResourceRevision).filter_by(resource_group_id=anna1.resource_groups[0].id).all()
        sorted_resources = sorted(resources_revisions, key=lambda x: (x.revision_timestamp, x.url))[::-1]

        for pkg in sorted_resources:
            print pkg.url, pkg.id, pkg.revision_timestamp, pkg.expired_timestamp, pkg.state, pkg.current

        assert len(sorted_resources) == 4
        assert sorted_resources[0].state == 'pending'
        assert sorted_resources[1].state == 'active'
        assert sorted_resources[1].current
        assert sorted_resources[2].state == 'active'
        assert sorted_resources[2].current
        assert sorted_resources[3].state == 'active'

        assert str(sorted_resources[0].expired_timestamp) == '9999-12-31 00:00:00'
        assert str(sorted_resources[1].expired_timestamp) != '9999-12-31 00:00:00'
        assert str(sorted_resources[2].expired_timestamp) == '9999-12-31 00:00:00'
        assert str(sorted_resources[3].expired_timestamp) != '9999-12-31 00:00:00'

        tag_revisions = model.Session.query(model.PackageTagRevision).filter_by(package_id=anna1.id).all()

        sorted_tags = sorted(tag_revisions, key=lambda x: (x.revision_timestamp, x.tag.name))[::-1]

        print [(tag.state, tag.tag.name) for tag in sorted_tags]

        assert len(sorted_tags) == 5, len(sorted_tags)
        assert sorted_tags[0].state == 'pending'            # new_tag
        assert sorted_tags[1].state == 'pending-deleted'    # Flexible
        assert sorted_tags[2].state == 'active'             # tolstoy
        assert sorted_tags[3].state == 'active'             # russian
        assert sorted_tags[4].state == 'active'             # Flexible
        assert sorted_tags[2].current
        assert sorted_tags[3].current
        assert sorted_tags[4].current

        assert str(sorted_tags[0].expired_timestamp) == '9999-12-31 00:00:00'
        assert str(sorted_tags[1].expired_timestamp) == '9999-12-31 00:00:00'
        assert str(sorted_tags[2].expired_timestamp) == '9999-12-31 00:00:00'
        assert str(sorted_tags[3].expired_timestamp) == '9999-12-31 00:00:00'
        assert str(sorted_tags[4].expired_timestamp) != '9999-12-31 00:00:00'

        extras_revisions = model.Session.query(model.PackageExtraRevision).filter_by(package_id=anna1.id).all()

        sorted_extras = sorted(extras_revisions, 
                               key=lambda x: (x.revision_timestamp, x.key))[::-1]

        assert sorted_extras[0].state == 'pending'
        assert sorted_resources[1].current
        assert sorted_extras[1].state == 'active'
        assert sorted_resources[1].current
        assert sorted_extras[2].state == 'active'

        assert str(sorted_extras[0].expired_timestamp) == '9999-12-31 00:00:00'
        assert str(sorted_extras[1].expired_timestamp) == '9999-12-31 00:00:00'
        assert str(sorted_extras[2].expired_timestamp) != '9999-12-31 00:00:00'


    def test_11_add_pending(self):

        context = {'model': model,
                   'session': model.Session,
                   'pending': True}

        anna1 = model.Session.query(model.Package).filter_by(name='annakarenina_changed2').one()
        anna_dictized = package_dictize(anna1, context)


        anna_dictized['notes'] = 'wee'
        anna_dictized['resources'].append({
                            'format': u'plain text',
                            'url': u'newurl'}
                            )
        anna_dictized['tags'].append({'name': u'newnew_tag'})
        anna_dictized['extras'].append({'key': 'david', 
                                        'value': u'"new_value"'})

        model.repo.new_revision()
        package_dict_save(anna_dictized, context)
        model.Session.commit()
        model.Session.remove()

        resources_revisions = model.Session.query(model.ResourceRevision).filter_by(resource_group_id=anna1.resource_groups[0].id).all()

        sorted_resources = sorted(resources_revisions, key=lambda x: (x.revision_timestamp, x.url))[::-1]
        pprint(anna_dictized['resources'])

        for pkg in sorted_resources:
            print pkg.url, pkg.id, pkg.revision_timestamp, pkg.expired_timestamp, pkg.state, pkg.current


        assert len(sorted_resources) == 5, len(sorted_resources)
        assert sorted_resources[0].state == 'pending'
        assert sorted_resources[1].state == 'pending'
        assert sorted_resources[2].current
        assert sorted_resources[2].state == 'active'
        assert sorted_resources[3].current
        assert sorted_resources[3].state == 'active'
        assert sorted_resources[4].state == 'active'

        assert str(sorted_resources[0].expired_timestamp) == '9999-12-31 00:00:00'
        assert str(sorted_resources[1].expired_timestamp) == '9999-12-31 00:00:00'
        assert str(sorted_resources[2].expired_timestamp) != '9999-12-31 00:00:00'
        assert str(sorted_resources[3].expired_timestamp) == '9999-12-31 00:00:00'
        assert str(sorted_resources[4].expired_timestamp) != '9999-12-31 00:00:00'

        tag_revisions = model.Session.query(model.PackageTagRevision).filter_by(package_id=anna1.id).all()

        sorted_tags = sorted(tag_revisions, key=lambda x: (x.revision_timestamp, x.tag.name))[::-1]

        print [(tag.state, tag.tag.name) for tag in sorted_tags]

        assert len(sorted_tags) == 6, len(sorted_tags)
        assert sorted_tags[0].state == 'pending'            # newnew_tag
        assert sorted_tags[1].state == 'pending'            # new_tag
        assert sorted_tags[2].state == 'pending-deleted'    # Flexible
        assert sorted_tags[3].state == 'active'             # tolstoy
        assert sorted_tags[4].state == 'active'             # russian
        assert sorted_tags[5].state == 'active'             # Flexible
        assert sorted_tags[3].current
        assert sorted_tags[4].current
        assert sorted_tags[5].current

        assert str(sorted_tags[0].expired_timestamp) == '9999-12-31 00:00:00'
        assert str(sorted_tags[1].expired_timestamp) == '9999-12-31 00:00:00'
        assert str(sorted_tags[2].expired_timestamp) == '9999-12-31 00:00:00'
        assert str(sorted_tags[3].expired_timestamp) == '9999-12-31 00:00:00'
        assert str(sorted_tags[4].expired_timestamp) == '9999-12-31 00:00:00'
        assert str(sorted_tags[5].expired_timestamp) != '9999-12-31 00:00:00'

        extras_revisions = model.Session.query(model.PackageExtraRevision).filter_by(package_id=anna1.id).all()

        sorted_extras = sorted(extras_revisions, 
                               key=lambda x: (x.revision_timestamp, x.key))[::-1]

        print [(extra.state, extra.key, extra.value) for extra in sorted_extras]

        assert sorted_extras[0].state == 'pending'
        assert sorted_extras[1].state == 'pending'
        assert sorted_extras[2].state == 'active'
        assert sorted_extras[3].state == 'active'

        assert str(sorted_extras[0].expired_timestamp) == '9999-12-31 00:00:00'
        assert str(sorted_extras[1].expired_timestamp) == '9999-12-31 00:00:00'
        assert str(sorted_extras[2].expired_timestamp) == '9999-12-31 00:00:00'
        assert str(sorted_extras[3].expired_timestamp) != '9999-12-31 00:00:00'

    def test_12_make_active(self):

        model.repo.new_revision()
        anna1 = model.Session.query(model.Package).filter_by(name='annakarenina_changed2').one()
        context = {"model": model,
                   "session": model.Session,
                   'user': 'testsysadmin'}

        make_latest_pending_package_active(context, {'id': anna1.id})

        pkgrevisions = model.Session.query(model.PackageRevision).filter_by(id=anna1.id).all()
        sorted_packages = sorted(pkgrevisions, key=lambda x:x.revision_timestamp)[::-1]

        assert len(sorted_packages) == 4
        assert sorted_packages[0].state == 'active', sorted_packages[0].state #was pending
        assert sorted_packages[0].current == True 

        assert sorted_packages[1].state == 'pending' 
        assert sorted_packages[2].state == 'active'
        assert sorted_packages[3].state == 'active'

        resources_revisions = model.Session.query(model.ResourceRevision).filter_by(resource_group_id=anna1.resource_groups[0].id).all()
        sorted_resources = sorted(resources_revisions, key=lambda x: (x.revision_timestamp, x.url))[::-1]

        assert len(sorted_resources) == 5
        for res in sorted_resources:
            print res.id, res.revision_timestamp, res.expired_timestamp, res.state
        assert sorted_resources[0].state == 'active'
        assert sorted_resources[0].current == True
        assert sorted_resources[1].state == 'active'
        assert sorted_resources[1].current == True
        assert sorted_resources[2].state == 'active'
        assert sorted_resources[3].state == 'active'
        assert sorted_resources[3].current == True
        assert sorted_resources[4].state == 'active'

        assert str(sorted_resources[0].expired_timestamp) == '9999-12-31 00:00:00'
        assert str(sorted_resources[1].expired_timestamp) == '9999-12-31 00:00:00'
        assert str(sorted_resources[2].expired_timestamp) != '9999-12-31 00:00:00'
        assert str(sorted_resources[3].expired_timestamp) == '9999-12-31 00:00:00'
        assert str(sorted_resources[4].expired_timestamp) != '9999-12-31 00:00:00'

        tag_revisions = model.Session.query(model.PackageTagRevision).filter_by(package_id=anna1.id).all()

        sorted_tags = sorted(tag_revisions, key=lambda x: (x.revision_timestamp, x.tag.name))[::-1]

        print [(tag.state, tag.tag.name) for tag in sorted_tags]
        
        assert len(sorted_tags) == 6, len(sorted_tags)
        assert sorted_tags[0].state == 'active'     # newnew_tag
        assert sorted_tags[1].state == 'active'     # new_tag
        assert sorted_tags[2].state == 'deleted'    # Flexible
        assert sorted_tags[3].state == 'active'     # tolstoy
        assert sorted_tags[4].state == 'active'     # russian
        assert sorted_tags[5].state == 'active'     # Flexible
        assert sorted_tags[0].current
        assert sorted_tags[1].current
        assert sorted_tags[2].current
        assert not sorted_tags[5].current

        assert str(sorted_tags[0].expired_timestamp) == '9999-12-31 00:00:00'
        assert str(sorted_tags[1].expired_timestamp) == '9999-12-31 00:00:00'
        assert str(sorted_tags[2].expired_timestamp) == '9999-12-31 00:00:00'
        assert str(sorted_tags[3].expired_timestamp) == '9999-12-31 00:00:00'
        assert str(sorted_tags[4].expired_timestamp) == '9999-12-31 00:00:00'
        assert str(sorted_tags[5].expired_timestamp) != '9999-12-31 00:00:00'

        extras_revisions = model.Session.query(model.PackageExtraRevision).filter_by(package_id=anna1.id).all()

        sorted_extras = sorted(extras_revisions, 
                               key=lambda x: (x.revision_timestamp, x.key))[::-1]

        print [(extra.state, extra.key, extra.value) for extra in sorted_extras]

        assert sorted_extras[0].state == 'active'
        assert sorted_extras[1].state == 'active'
        assert sorted_extras[2].state == 'active'
        assert sorted_extras[3].state == 'active'

        assert str(sorted_extras[0].expired_timestamp) == '9999-12-31 00:00:00'
        assert str(sorted_extras[1].expired_timestamp) == '9999-12-31 00:00:00'
        assert str(sorted_extras[2].expired_timestamp) == '9999-12-31 00:00:00'
        assert str(sorted_extras[3].expired_timestamp) != '9999-12-31 00:00:00'

    def test_13_get_package_in_past(self):

        context = {'model': model,
                   'session': model.Session}

        anna1 = model.Session.query(model.Package).filter_by(name='annakarenina_changed2').one()

        pkgrevisions = model.Session.query(model.PackageRevision).filter_by(id=anna1.id).all()
        sorted_packages = sorted(pkgrevisions, key=lambda x:x.revision_timestamp)

        context['revision_id'] = sorted_packages[0].revision_id #original state

        first_dictized = self.remove_changable_columns(package_dictize(anna1, context))
        assert self.package_expected == first_dictized

        context['revision_id'] = sorted_packages[1].revision_id #original state

        second_dictized = self.remove_changable_columns(package_dictize(anna1, context))

        first_dictized["name"] = u'annakarenina_changed' 
        first_dictized["resources"][0]["url"] = u'new_url' 

        assert second_dictized == first_dictized

        context['revision_id'] = sorted_packages[2].revision_id #original state
        third_dictized = self.remove_changable_columns(package_dictize(anna1, context))
        
        second_dictized['name'] = u'annakarenina_changed2' 
        second_dictized['resources'][0]['url'] = u'new_url2' 
        second_dictized['tags'][0]['name'] = u'new_tag' 
        second_dictized['extras'][0]['value'] = u'"new_value"' 
        second_dictized['state'] = 'pending'

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
            u'size': None,
            u'state': u'active',
            u'url': u'newurl',
            u'webstore_last_updated': None,
            u'webstore_url': None})

        third_dictized['tags'].insert(1, {'name': u'newnew_tag', 'state': 'active'})
        third_dictized['extras'].insert(0, {'key': 'david', 
                                         'value': u'"new_value"',
                                         'state': u'active'})
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
            'url': u'test_new',
            'cache_url': None,
            'webstore_url': None,
            'cache_last_updated': None,
            'state': u'active',
            'mimetype_inner': None,
            'webstore_last_updated': None,
            'last_modified': None,
            'position': 0,
            'size': None,
            'size_extra': u'123',
            'resource_type': None,
            'name': None}

        model.repo.new_revision()
        resource_dict_save(new_resource, context)
        model.Session.commit()
        model.Session.remove()

        res = model.Session.query(model.Resource).filter_by(url=u'test_new').one()

        res_dictized = self.remove_changable_columns(resource_dictize(res, context))

        assert res_dictized == new_resource, res_dictized 

    def test_15_api_to_dictize(self):

        context = {"model": model,
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

        assert dictized == {'extras': [{'key': 'genre', 'value': u'"horror"'},
                                       {'key': 'media', 'value': u'"dvd"'}],
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

    def test_16_group_dictized(self):

        context = {"model": model,
                  "session": model.Session}

        pkg = model.Session.query(model.Package).filter_by(name='annakarenina3').first()

        simple_group_dict = {'name': 'simple',
                             'title': 'simple',
                             'type': 'publisher',
                            }
        model.repo.new_revision()
        group_dict_save(simple_group_dict, context)
        model.Session.commit()
        model.Session.remove()

        context = {"model": model,
                  "session": model.Session}

        group_dict = {'name': 'help',
                      'title': 'help',
                      'extras': [{'key': 'genre', 'value': u'"horror"'},
                                 {'key': 'media', 'value': u'"dvd"'}],
                      'packages':[{'name': 'annakarenina2'}, {'id': pkg.id, 'capacity': 'in'}],
                      'users':[{'name': 'annafan'}],
                      'groups':[{'name': 'simple'}],
                      'tags':[{'name': 'russian'}]
                      }

        model.repo.new_revision()
        group_dict_save(group_dict, context)
        model.Session.commit()
        model.Session.remove()
        
        group = model.Session.query(model.Group).filter_by(name=u'help').one()

        context = {"model": model,
                  "session": model.Session}

        group_dictized = group_dictize(group, context)

        expected =  {'description': u'',
                    'extras': [{'key': u'genre', 'state': u'active', 'value': u'"horror"'},
                               {'key': u'media', 'state': u'active', 'value': u'"dvd"'}],
                    'tags': [{'capacity': 'member', 'name': u'russian'}],
                    'groups': [{'description': u'',
                               'capacity' : 'member',
                               'display_name': u'simple',
                               'name': u'simple',
                               'packages': 0,
                               'state': u'active',
                               'title': u'simple',
                               'type': u'publisher'}],
                    'users': [{'about': u'I love reading Annakarenina. My site: <a href="http://anna.com">anna.com</a>',
                              'display_name': u'annafan',
                              'capacity' : 'member',
                              'email': None,
                              'email_hash': 'd41d8cd98f00b204e9800998ecf8427e',
                              'fullname': None,
                              'name': u'annafan',
                              'number_administered_packages': 1L,
                              'number_of_edits': 0L,
                              'reset_key': None}],
                    'name': u'help',
                    'display_name': u'help',
                    'packages': [{'author': None,
                                  'author_email': None,
                                  'license_id': u'other-open',
                                  'maintainer': None,
                                  'maintainer_email': None,
                                  'type': None,
                                  'name': u'annakarenina3',
                                  'notes': u'Some test notes\n\n### A 3rd level heading\n\n**Some bolded text.**\n\n*Some italicized text.*\n\nForeign characters:\nu with umlaut \xfc\n66-style quote \u201c\nforeign word: th\xfcmb\n \nNeeds escaping:\nleft arrow <\n\n<http://ckan.net/>\n\n',
                                  'state': u'active',
                                  'capacity' : 'in',
                                  'title': u'A Novel By Tolstoy',
                                  'url': u'http://www.annakarenina.com',
                                  'version': u'0.7a'},
                                 {'author': None,
                                  'author_email': None,
                                  'capacity' : 'member',
                                  'title': u'A Novel By Tolstoy',
                                  'license_id': u'other-open',
                                  'maintainer': None,
                                  'maintainer_email': None,
                                  'type': None,
                                  'name': u'annakarenina2',
                                  'notes': u'Some test notes\n\n### A 3rd level heading\n\n**Some bolded text.**\n\n*Some italicized text.*\n\nForeign characters:\nu with umlaut \xfc\n66-style quote \u201c\nforeign word: th\xfcmb\n \nNeeds escaping:\nleft arrow <\n\n<http://ckan.net/>\n\n',
                                  'state': u'active',
                                  'title': u'A Novel By Tolstoy',
                                  'url': u'http://www.annakarenina.com',
                                  'version': u'0.7a'}],
                    'state': u'active',
                    'title': u'help',
                    'type': u'group'}

        expected['packages'] = sorted(expected['packages'], key=lambda x: x['name'])

        result = self.remove_changable_columns(group_dictized)

        result['packages'] = sorted(result['packages'], key=lambda x: x['name'])

        assert result == expected, pformat(result)


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
        assert_equal(set([tag.name for tag in pkg.tags]), set(('tag1', 'tag2')))

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
        assert_equal(set([tag.name for tag in pkg.tags]), set(('tag1',)))

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
