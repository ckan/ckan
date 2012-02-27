import json
from pylons import request, tmpl_context as c
from genshi.input import HTML
from genshi.filters import Transformer
import paste.fixture
from ckan import model
from ckan.logic import get_action
from ckan.logic.converters import convert_to_tags, convert_from_tags, free_tags_only
from ckan.logic.schema import package_form_schema
from ckan.lib.navl.validators import ignore_missing, keep_extras
from ckan.lib.create_test_data import CreateTestData
import ckan.lib.helpers as h
from ckan import plugins
from ckan.tests import WsgiAppCase, url_for

TEST_VOCAB_NAME = 'test-vocab'

class MockVocabTagsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IDatasetForm, inherit=True)
    plugins.implements(plugins.IGenshiStreamFilter)

    active = False

    def is_fallback(self):
        return False

    def package_types(self):
        return ["mock_vocab_tags_plugin"]

    def package_form(self):
        return 'package/new_package_form.html'

    def setup_template_variables(self, context, data_dict=None):
        c.vocab_tags = get_action('tag_list')(context, {'vocabulary_id': TEST_VOCAB_NAME})

    def form_to_db_schema(self):
        schema = package_form_schema()
        schema.update({
            'vocab_tags': [ignore_missing, convert_to_tags(TEST_VOCAB_NAME)],
        })
        return schema

    def db_to_form_schema(self):
        schema = package_form_schema()
        schema.update({
            'tags': {
                '__extras': [keep_extras, free_tags_only]
            },
            'vocab_tags_selected': [convert_from_tags(TEST_VOCAB_NAME), ignore_missing],
        })
        return schema

    def filter(self, stream):
        if self.active:
            routes = request.environ.get('pylons.routes_dict')
            if routes.get('controller') == 'package' \
                and routes.get('action') == 'read':
                    # add vocab tags to the bottom of the page
                    tags = c.pkg_dict.get('tags', [])
                    for tag in tags:
                        if tag.get('vocabulary_id'):
                            stream = stream | Transformer('body')\
                                .append(HTML('<p>%s</p>' % tag.get('name')))
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
                    stream = stream | Transformer('fieldset[@id="groups"]').append(HTML(html))
        return stream


# paste.fixture.Field.Select does not handle multiple selects currently,
# so replace with our own implementations of Form and Select
class Form(paste.fixture.Form):
    def __init__(self, response, text):
        paste.fixture.Form.__init__(self, response, text)

    def submit_fields(self, name=None, index=None):
        """
        Return a list of ``[(name, value), ...]`` for the current
        state of the form.
        """
        submit = []
        if name is not None:
            field = self.get(name, index=index)
            submit.append((field.name, field.value_if_submitted()))
        for name, fields in self.fields.items():
            if name is None:
                continue
            for field in fields:
                value = field.value
                if value is None:
                    continue
                if isinstance(value, list):
                    for v in value:
                        submit.append((name, v))
                else:
                    submit.append((name, value))
        return submit


class Select(paste.fixture.Field):
    def __init__(self, *args, **attrs):
        paste.fixture.Field.__init__(self, *args, **attrs)
        self.options = []
        self.selectedIndex = None

    def value__set(self, value):
        if not value:
            self.selectedIndex = None
            self.options = [(option, False) for (option, checked) in self.options]
            return

        for v in value:
            if not v in [option for (option, checked) in self.options]:
                raise ValueError("Option %r not found (from %s)"
                    % (value, ', '.join(
                    [repr(o) for o, checked in self.options]))
                )

        new_options = [(option, True) for (option, checked) in self.options if option in value]
        new_options += [(option, False) for (option, checked) in self.options if not option in value]
        self.options = new_options

    def value__get(self):
        return [option for (option, checked) in self.options if checked]

    value = property(value__get, value__set)

class TestWUI(WsgiAppCase):
    @classmethod
    def setup_class(cls):
        CreateTestData.create(package_type='mock_vocab_tags_plugin')
        cls.sysadmin_user = model.User.get('testsysadmin')
        cls.dset = model.Package.get('warandpeace')
        cls.tag1_name = 'vocab-tag-1'
        cls.tag2_name = 'vocab-tag-2'

        cls.plugin = MockVocabTagsPlugin()
        plugins.load(cls.plugin)
        cls.plugin.active = True

        # use our custom select class for this test suite
        cls.old_select = paste.fixture.Field.classes['select']
        paste.fixture.Field.classes['select'] = Select

        # create a test vocab
        params = json.dumps({'name': TEST_VOCAB_NAME})
        extra_environ = {'Authorization' : str(cls.sysadmin_user.apikey)}
        response = cls.app.post('/api/action/vocabulary_create', params=params,
                                extra_environ=extra_environ)
        assert json.loads(response.body)['success']
        vocab_id = json.loads(response.body)['result']['id']

        # add tags to the vocab
        extra_environ = {'Authorization' : str(cls.sysadmin_user.apikey)}
        params = json.dumps({'name': cls.tag1_name, 'vocabulary_id': vocab_id})
        response = cls.app.post('/api/action/tag_create', params=params,
                                 extra_environ=extra_environ)
        assert json.loads(response.body)['success']
        params = json.dumps({'name': cls.tag2_name, 'vocabulary_id': vocab_id})
        response = cls.app.post('/api/action/tag_create', params=params,
                                 extra_environ=extra_environ)
        assert json.loads(response.body)['success']

    @classmethod
    def teardown_class(cls):
        plugins.unload(cls.plugin)
        cls.plugin.active = False
        paste.fixture.Field.classes['select'] = cls.old_select
        model.repo.rebuild_db()

    def _get_vocab_id(self, vocab_name):
        params = json.dumps({'id': vocab_name})
        response = self.app.post('/api/action/vocabulary_show', params=params)
        assert json.loads(response.body)['success']
        return json.loads(response.body)['result']['id']

    def _add_vocab_tag_to_dataset(self, dataset_id, vocab_id, tag_name):
        params = json.dumps({'id': dataset_id})
        response = self.app.post('/api/action/package_show', params=params)
        dataset = json.loads(response.body)['result']
        dataset['tags'].append({'name': tag_name, 'vocabulary_id': vocab_id})
        params = json.dumps(dataset)
        response = self.app.post('/api/action/package_update', params=params,
                                 extra_environ={'Authorization': str(self.sysadmin_user.apikey)})
        assert json.loads(response.body)['success']

    def _remove_vocab_tags(self, dataset_id, vocab_id, tag_name):
        params = json.dumps({'id': dataset_id})
        response = self.app.post('/api/action/package_show', params=params)
        dataset = json.loads(response.body)['result']
        dataset['tags'] = [t for t in dataset['tags'] if not t['name'] == tag_name]
        params = json.dumps(dataset)
        response = self.app.post('/api/action/package_update', params=params,
                                 extra_environ={'Authorization': str(self.sysadmin_user.apikey)})
        assert json.loads(response.body)['success']

    def test_01_dataset_view(self):
        vocab_id = self._get_vocab_id(TEST_VOCAB_NAME)
        self._add_vocab_tag_to_dataset(self.dset.id, vocab_id, self.tag1_name)
        response = self.app.get(h.url_for(controller='package', action='read',
            id=self.dset.id))
        assert self.tag1_name in response.body
        self._remove_vocab_tags(self.dset.id, vocab_id, self.tag1_name)

    def test_02_dataset_edit_add_vocab_tag(self):
        vocab_id = self._get_vocab_id(TEST_VOCAB_NAME)
        url = h.url_for(controller='package', action='edit', id=self.dset.id)
        response = self.app.get(url)
        fv = response.forms['dataset-edit']
        fv = Form(fv.response, fv.text)
        fv['vocab_tags'] = [self.tag2_name]
        response = fv.submit('save')
        response = response.follow()
        assert not self.tag1_name in response.body
        assert self.tag2_name in response.body
        self._remove_vocab_tags(self.dset.id, vocab_id, self.tag1_name)
        self._remove_vocab_tags(self.dset.id, vocab_id, self.tag2_name)

    def test_02_dataset_edit_add_free_and_vocab_tags_then_edit_again(self):
        vocab_id = self._get_vocab_id(TEST_VOCAB_NAME)
        url = h.url_for(controller='package', action='edit', id=self.dset.id)
        response = self.app.get(url)
        fv = response.forms['dataset-edit']
        fv = Form(fv.response, fv.text)

        # Add a free tag with a space in its name.
        fv['tag_string'] = 'water quality'

        # Add a vocab tag.
        fv['vocab_tags'] = [self.tag2_name]

        # Save the dataset and visit the page again
        response = fv.submit('save')
        response = response.follow()
        assert not self.tag1_name in response.body
        assert self.tag2_name in response.body
        url = h.url_for(controller='package', action='edit', id=self.dset.id)
        response = self.app.get(url)
        fv = response.forms['dataset-edit']
        fv = Form(fv.response, fv.text)
        assert fv['vocab_tags'].value == [self.tag2_name], fv['vocab_tags'].value
        self._remove_vocab_tags(self.dset.id, vocab_id, self.tag2_name)

    def test_03_dataset_edit_remove_vocab_tag(self):
        vocab_id = self._get_vocab_id(TEST_VOCAB_NAME)
        self._add_vocab_tag_to_dataset(self.dset.id, vocab_id, self.tag1_name)
        url = h.url_for(controller='package', action='edit', id=self.dset.id)
        response = self.app.get(url)
        fv = response.forms['dataset-edit']
        fv = Form(fv.response, fv.text)
        fv['vocab_tags'] = []
        response = fv.submit('save')
        response = response.follow()
        assert not self.tag1_name in response.body
        self._remove_vocab_tags(self.dset.id, vocab_id, self.tag1_name)

    def test_04_dataset_edit_change_vocab_tag(self):
        vocab_id = self._get_vocab_id(TEST_VOCAB_NAME)
        self._add_vocab_tag_to_dataset(self.dset.id, vocab_id, self.tag1_name)
        url = h.url_for(controller='package', action='edit', id=self.dset.id)
        response = self.app.get(url)
        fv = response.forms['dataset-edit']
        fv = Form(fv.response, fv.text)
        fv['vocab_tags'] = [self.tag2_name]
        response = fv.submit('save')
        response = response.follow()
        assert not self.tag1_name in response.body
        assert self.tag2_name in response.body
        self._remove_vocab_tags(self.dset.id, vocab_id, self.tag2_name)

    def test_05_dataset_edit_add_multiple_vocab_tags(self):
        vocab_id = self._get_vocab_id(TEST_VOCAB_NAME)
        url = h.url_for(controller='package', action='edit', id=self.dset.id)
        response = self.app.get(url)
        fv = response.forms['dataset-edit']
        fv = Form(fv.response, fv.text)
        fv['vocab_tags'] = [self.tag1_name, self.tag2_name]
        response = fv.submit('save')
        response = response.follow()
        assert self.tag1_name in response.body
        assert self.tag2_name in response.body
        self._remove_vocab_tags(self.dset.id, vocab_id, self.tag1_name)
        self._remove_vocab_tags(self.dset.id, vocab_id, self.tag2_name)

