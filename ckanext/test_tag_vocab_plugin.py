# encoding: utf-8

''' THIS PLUGIN IS FOR TESTING PURPOSES ONLY.
Currently this is used in tests/functional/test_tag_vocab.py'''


from ckan.common import c
from ckan.logic import get_action
from ckan.logic.converters import convert_to_tags, convert_from_tags, free_tags_only
from ckan.logic.schema import default_create_package_schema, default_update_package_schema, default_show_package_schema
from ckan.lib.navl.validators import ignore_missing, keep_extras
from ckan import plugins

TEST_VOCAB_NAME = 'test-vocab'

class MockVocabTagsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IDatasetForm, inherit=True)

    def is_fallback(self):
        return False

    def package_types(self):
        return ["mock_vocab_tags_plugin"]

    def new_template(self):
        return 'package/new.html'

    def edit_template(self):
        return 'package/edit.html'

    def search_template(self):
        return 'package/search.html'

    def read_template(self):
        return 'package/read.html'

    def package_form(self):
        return 'package/new_package_form.html'

    def setup_template_variables(self, context, data_dict=None):
        c.vocab_tags = get_action('tag_list')(context, {'vocabulary_id': TEST_VOCAB_NAME})

    def create_package_schema(self):
        schema = default_create_package_schema()
        schema.update({
            'vocab_tags': [ignore_missing, convert_to_tags(TEST_VOCAB_NAME)],
        })
        return schema

    def update_package_schema(self):
        schema = default_update_package_schema()
        schema.update({
            'vocab_tags': [ignore_missing, convert_to_tags(TEST_VOCAB_NAME)],
        })
        return schema

    def show_package_schema(self):
        schema = default_show_package_schema()
        schema.update({
            'tags': {
                '__extras': [keep_extras, free_tags_only]
            },
            'vocab_tags_selected': [convert_from_tags(TEST_VOCAB_NAME), ignore_missing],
        })
        return schema
