# encoding: utf-8

from nose.tools import assert_equal

import ckan
from ckan.lib.navl.dictization_functions import validate
import ckan.logic.schema

class TestPackage:
    def test_name_validation(self):
        context = {'model': ckan.model,
                   'session': ckan.model.Session}
        schema = ckan.logic.schema.default_create_package_schema()
        def get_package_name_validation_errors(package_name):
            data_dict = {'name': package_name}
            data, errors = validate(data_dict, schema, context)
            return errors.get('name', [])

        good_names = ('blah', 'ab', 'ab1', 'some-random-made-up-name', 'has_underscore', 'annakarenina')
        bad_names = (('', [u'Missing value']),
                     ('blAh', [u'Must be purely lowercase alphanumeric (ascii) characters and these symbols: -_']),
                     ('a', [u'Must be at least 2 characters long', u'Name NAME length is less than minimum 2']),
                     ('dot.in.name', [u'Must be purely lowercase alphanumeric (ascii) characters and these symbols: -_']),
                     (u'unicode-\xe0', [u'Must be purely lowercase alphanumeric (ascii) characters and these symbols: -_']),
                     ('percent%', [u'Must be purely lowercase alphanumeric (ascii) characters and these symbols: -_']),
                     ('p'*101, [u'Name must be a maximum of 100 characters long', u'Name NAME length is more than maximum 100']),
                     )

        for package_name in good_names:
            errors = get_package_name_validation_errors(package_name)
            assert_equal(errors, [])

        for package_name, expected_errors in bad_names:
            errors = get_package_name_validation_errors(package_name)
            errors = [err.replace('"%s"' % package_name, 'NAME') for err in errors]
            assert errors==expected_errors, \
                   '%r: %r != %r' % (package_name, errors, expected_errors)

    def test_version_validation(self):
        context = {'model': ckan.model,
                   'session': ckan.model.Session}
        schema = ckan.logic.schema.default_create_package_schema()
        def get_package_version_validation_errors(package_version):
            data_dict = {'version': package_version}
            data, errors = validate(data_dict, schema, context)
            return errors.get('version', [])

        good_versions = ('1.0', '')
        bad_versions = (
                     ('p'*101, [u'Version must be a maximum of 100 characters long']),
                     )

        for package_version in good_versions:
            errors = get_package_version_validation_errors(package_version)
            assert_equal(errors, [])

        for package_version, expected_errors in bad_versions:
            errors = get_package_version_validation_errors(package_version)
            errors = [err.replace('"%s"' % package_version, 'VERSION') for err in errors]
            assert errors==expected_errors, \
                   '%r: %r != %r' % (package_version, errors, expected_errors)


    def test_convert_from_extras(self):
        from ckan import logic
        context = {'model': ckan.model,
                   'session': ckan.model.Session}
        schema = ckan.logic.schema.default_create_package_schema()
        schema.update({
            'my_field': [logic.converters.convert_from_extras]
        })
        data_dict = {
            'name': 'my-pkg',
            'extras': [
                {'key': 'my_field', 'value': 'hola'},
                {'key': 'another_extra', 'value': 'caracola'}
                ]
            }
        data, errors = validate(data_dict, schema, context)

        assert 'my_field' in data
        assert data['my_field'] == 'hola'
        assert data['extras'][0]['key'] ==  'another_extra'

class TestTag:
    def test_tag_name_validation(self):
        context = {'model': ckan.model}
        schema = ckan.logic.schema.default_tags_schema()
        def get_tag_validation_errors(tag_name):
            data_dict = {'name': tag_name}

            data, errors = validate(data_dict, schema, context)
            return errors.get('name', [])

        good_names = ('blah', 'ab', 'ab1', 'some-random-made-up-name',\
                      'has_underscore', u'unicode-\xe0', 'dot.in.name',\
                      'multiple words', u'with Greek omega \u03a9', 'CAPITALS')
        bad_names = (('a', [u'Tag TAG length is less than minimum 2']),
                     ('  ,leading comma', [u'Tag TAG must be alphanumeric characters or symbols: -_.']),
                     ('trailing comma,', [u'Tag TAG must be alphanumeric characters or symbols: -_.']),\
                     ('empty,,tag', [u'Tag TAG must be alphanumeric characters or symbols: -_.']),
                     ('quote"character', [u'Tag TAG must be alphanumeric characters or symbols: -_.']),
                     ('p'*101, [u'Tag TAG length is more than maximum 100']),
                     )

        for tag_name in good_names:
            errors = get_tag_validation_errors(tag_name)
            assert_equal(errors, [])

        for tag_name, expected_errors in bad_names:
            errors = get_tag_validation_errors(tag_name)
            errors = [err.replace('"%s"' % tag_name, 'TAG') for err in errors]
            assert_equal(errors, expected_errors)

    def test_tag_string_parsing(self):
        # 'tag_string' is what you type into the tags field in the package
        # edit form. This test checks that it is parsed correctly or reports
        # errors correctly.
        context = {'model': ckan.model,
                   'session': ckan.model.Session}
        schema = ckan.logic.schema.default_update_package_schema()

        # basic parsing of comma separated values
        tests = (('tag', ['tag'], []),
                 ('tag1, tag2', ['tag1', 'tag2'], []),
                 ('tag 1', ['tag 1'], []),
                 )
        for tag_string, expected_tags, expected_errors in tests:
            data_dict = {'tag_string': tag_string}
            data, errors = validate(data_dict, schema, context)
            assert_equal(errors.get('tags', []), expected_errors)
            tag_names = [tag_dict['name'] for tag_dict in data['tags']]
            assert_equal(tag_names, expected_tags)
            
        # test whitespace chars are stripped
        whitespace_characters = u'\t\n\r\f\v '
        for ch in whitespace_characters:
            tag = ch + u'tag name' + ch
            data_dict = {'tag_string': tag}
            data, errors = validate(data_dict, schema, context)
            assert_equal(data['tags'], [{'name': u'tag name'}])


