''' THIS PLUGIN IS FOR TESTING PURPOSES ONLY.
Currently this is used in tests/functional/test_tag_vocab.py'''


from pylons import request, tmpl_context as c
from genshi.input import HTML
from genshi.filters import Transformer
from ckan.logic import get_action
from ckan.logic.converters import convert_to_tags, convert_from_tags, free_tags_only
from ckan.logic.schema import default_package_schema
from ckan.lib.navl.validators import ignore_missing, keep_extras
from ckan import plugins

TEST_VOCAB_NAME = 'test-vocab'

class MockVocabTagsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IDatasetForm, inherit=True)
    plugins.implements(plugins.IGenshiStreamFilter)

    active = False

    def is_fallback(self):
        return False

    def package_types(self):
        return ["mock_vocab_tags_plugin"]

    def new_template(self):
        return 'package/new.html'

    def comments_template(self):
        return 'package/comments.html'

    def search_template(self):
        return 'package/search.html'

    def read_template(self):
        return 'package/read.html'

    def history_template(self):
        return 'package/history.html'

    def package_form(self):
        return 'package/new_package_form.html'

    def setup_template_variables(self, context, data_dict=None):
        c.vocab_tags = get_action('tag_list')(context, {'vocabulary_id': TEST_VOCAB_NAME})

    def form_to_db_schema(self):
        schema = default_package_schema()
        schema.update({
            'vocab_tags': [ignore_missing, convert_to_tags(TEST_VOCAB_NAME)],
        })
        return schema

    def db_to_form_schema(self):
        schema = default_package_schema()
        schema.update({
            'tags': {
                '__extras': [keep_extras, free_tags_only]
            },
            'vocab_tags_selected': [convert_from_tags(TEST_VOCAB_NAME), ignore_missing],
        })
        return schema

    def set_active(self, state):
        self.active = state

    def filter(self, stream):
        if self.active:
            routes = request.environ.get('pylons.routes_dict')
            if routes.get('controller') == 'package' \
                and routes.get('action') == 'read':
                    # add vocab tags to the bottom of the page
                    tags = c.pkg_dict.get('vocab_tags_selected', [])
                    for tag in tags:
                        stream = stream | Transformer('body')\
                            .append(HTML('<p>%s</p>' % tag))
            if routes.get('controller') == 'package' \
                and routes.get('action') == 'edit':
                    # add vocabs tag select box to edit page
                    html = '<select id="vocab_tags" name="vocab_tags" size="60" multiple="multiple">'
                    selected_tags = c.pkg_dict.get('vocab_tags_selected', [])
                    for tag in c.vocab_tags:
                        if tag in selected_tags:
                            html += '<option selected="selected" value="%s">%s</option>' % (tag, tag)
                        else:
                            html += '<option value="%s">%s</option>' % (tag, tag)
                    html += '</select>'
                    stream = stream | Transformer('fieldset[@id="basic-information"]').append(HTML(html))
        return stream
