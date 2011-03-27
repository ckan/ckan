from nose.tools import assert_equal
from pprint import pprint, pformat
from difflib import unified_diff

from ckan.lib.create_test_data import CreateTestData
from ckan import model
from ckan.lib.dictization import (table_dictize,
                              table_dict_save)

from ckan.lib.dictization.model_dictize import (package_dictize,
                                                resource_dictize,
                                                package_to_api1,
                                                package_to_api2)

from ckan.lib.dictization.model_save import (package_dict_save,
                                             resource_dict_save)

class TestBasicDictize:
    @classmethod
    def setup_class(cls):
        CreateTestData.create()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()
        model.Session.remove()

    def remove_changable_columns(self, dict):
        for key, value in dict.items():
            if key.endswith('id') and key <> 'license_id':
                dict.pop(key)
            if isinstance(value, list):
                for new_dict in value:
                    self.remove_changable_columns(new_dict)
        return dict

    def remove_revision_id(self, dict):
        for key, value in dict.items():
            if key == 'revision_id':
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
            'notes': u'Some test notes\n\n### A 3rd level heading\n\n**Some bolded text.**\n\n*Some italicized text.*\n\nForeign characters:\nu with umlaut \xfc\n66-style quote \u201c\nforeign word: th\xfcmb\n \nNeeds escaping:\nleft arrow <\n\n<http://ckan.net/>\n\n',
            'state': u'active',
            'title': u'A Novel By Tolstoy',
            'url': u'http://www.annakarenina.com',
            'version': u'0.7a'
        }, pprint(result)

        ## resource

        resource = pkg.resource_groups[0].resources[0]

        result = table_dictize(resource, context)
        self.remove_changable_columns(result)

        assert result == {
            'alt_url': u'alt123',
            'description': u'Full text. Needs escaping: " Umlaut: \xfc',
            'extras': {u'alt_url': u'alt123', u'size': u'123'},
            'format': u'plain text',
            'hash': u'abc123',
            'position': 0,
            'state': u'active',
            'url': u'http://www.annakarenina.com/download/x=1&y=2'
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

        pkg = model.Session.query(model.Package).filter_by(name='annakarenina').first()

        result = package_dictize(pkg, context)
        self.remove_changable_columns(result)

        
        assert result ==\
            {'author': None,
             'author_email': None,
             'extras': [{'key': u'original media', 'state': u'active', 'value': u'book'}],
             'groups': [{'description': u'These are books that David likes.',
                         'name': u'david',
                         'state': u'active',
                         'title': u"Dave's books"},
                        {'description': u'Roger likes these books.',
                         'name': u'roger',
                         'state': u'active',
                         'title': u"Roger's books"}],
             'license_id': u'other-open',
             'maintainer': None,
             'maintainer_email': None,
             'name': u'annakarenina',
             'notes': u'Some test notes\n\n### A 3rd level heading\n\n**Some bolded text.**\n\n*Some italicized text.*\n\nForeign characters:\nu with umlaut \xfc\n66-style quote \u201c\nforeign word: th\xfcmb\n \nNeeds escaping:\nleft arrow <\n\n<http://ckan.net/>\n\n',
             'relationships_as_object': [],
             'relationships_as_subject': [],
             'resources': [{'alt_url': u'alt123',
                            'description': u'Full text. Needs escaping: " Umlaut: \xfc',
                            'extras': {u'alt_url': u'alt123', u'size': u'123'},
                            'format': u'plain text',
                            'hash': u'abc123',
                            'position': 0,
                            'state': u'active',
                            'url': u'http://www.annakarenina.com/download/x=1&y=2'},
                           {'alt_url': u'alt345',
                            'description': u'Index of the novel',
                            'extras': {u'alt_url': u'alt345', u'size': u'345'},
                            'format': u'json',
                            'hash': u'def456',
                            'position': 1,
                            'state': u'active',
                            'url': u'http://www.annakarenina.com/index.json'}],
             'state': u'active',
             'tags': [{'name': u'russian'}, {'name': u'tolstoy'}],
             'title': u'A Novel By Tolstoy',
             'url': u'http://www.annakarenina.com',
             'version': u'0.7a'}, pprint(result)



    def test_03_package_to_api1(self):

        context = {"model": model,
                 "session": model.Session}

        pkg = model.Session.query(model.Package).filter_by(name='annakarenina').first()

        pprint(package_to_api1(pkg, context))
        pprint(pkg.as_dict())

        assert package_to_api1(pkg, context) == pkg.as_dict()

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
        print anna_original
        print anna_after_save

        assert self.remove_changable_columns(package_dictize(pkg, context)) == anna_dictized, "\n".join(unified_diff(anna_original.split("\n"), anna_after_save.split("\n")))

    def test_10_package_alter(self):

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

        anna_original = pformat(anna_dictized)
        anna_after_save = pformat(package_dictized)

        print anna_original
        print anna_after_save

        assert self.remove_revision_id(anna_dictized) == self.remove_revision_id(package_dictized),\
                "\n".join(unified_diff(anna_original.split("\n"), anna_after_save.split("\n")))


    def test_11_resource_no_id(self):

        context = {"model": model,
                 "session": model.Session}

        model.repo.new_revision()
        model.Session.commit()

        new_resource = {
            'alt_url': u'empty resource group id',
            'description': u'Full text. Needs escaping: " Umlaut: \xfc',
            'extras': {u'alt_url': u'empty resource group id', u'size': u'123'},
            'format': u'plain text',
            'hash': u'abc123',
            'position': 0,
            'state': u'active',
            'url': u'test'
        }

        model.repo.new_revision()
        resource_dict_save(new_resource, context)
        model.Session.commit()
        model.Session.remove()

        res = model.Session.query(model.Resource).filter_by(url=u'test').one()


        res_dictized = self.remove_changable_columns(resource_dictize(res, context))

        pprint(res_dictized)
        pprint(new_resource)

        assert res_dictized == new_resource, res_dictized 



