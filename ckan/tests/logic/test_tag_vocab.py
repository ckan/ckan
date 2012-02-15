import json
from pylons import request, tmpl_context as c
from genshi.input import HTML
from genshi.filters import Transformer
import paste.fixture
from ckan import model
from ckan.logic import get_action
from ckan.logic.converters import convert_to_tags, convert_from_tags, free_tags_only
from ckan.logic.schema import package_form_schema
from ckan.lib.navl.dictization_functions import unflatten
from ckan.lib.navl.validators import ignore_missing, keep_extras
from ckan.lib.create_test_data import CreateTestData
import ckan.lib.helpers as h
from ckan import plugins
from ckan.tests import WsgiAppCase

TEST_VOCAB_NAME = 'test-vocab'

class TestConverters(object):
    @classmethod
    def setup_class(cls):
        cls.vocab = model.Vocabulary(TEST_VOCAB_NAME) 
        model.Session.add(cls.vocab)
        model.Session.commit()
        vocab_tag_1 = model.Tag('tag1', cls.vocab.id)
        vocab_tag_2 = model.Tag('tag2', cls.vocab.id)
        model.Session.add(vocab_tag_1)
        model.Session.add(vocab_tag_2)
        model.Session.commit()
        model.Session.remove()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_convert_to_tags(self):
        def convert(tag_string, vocab):
            key = 'vocab_tags'
            data = {key: tag_string}
            errors = []
            context = {'model': model, 'session': model.Session}
            convert_to_tags(vocab)(key, data, errors, context)
            del data[key]
            return data

        data = unflatten(convert(['tag1', 'tag2'], 'test-vocab'))
        for tag in data['tags']:
            assert tag['name'] in ['tag1', 'tag2'], tag['name']
            assert tag['vocabulary_id'] == self.vocab.id, tag['vocabulary_id']

    def test_convert_from_tags(self):
        key = 'tags'
        data = {
            ('tags', 0, '__extras'): {'name': 'tag1', 'vocabulary_id': self.vocab.id},
            ('tags', 1, '__extras'): {'name': 'tag2', 'vocabulary_id': self.vocab.id}
        }
        errors = []
        context = {'model': model, 'session': model.Session}
        convert_from_tags(self.vocab.name)(key, data, errors, context)
        assert 'tag1' in data['tags']
        assert 'tag2' in data['tags']

    def test_free_tags_only(self):
        key = ('tags', 0, '__extras')
        data = {
            ('tags', 0, '__extras'): {'name': 'tag1', 'vocabulary_id': self.vocab.id},
            ('tags', 0, 'vocabulary_id'): self.vocab.id,
            ('tags', 1, '__extras'): {'name': 'tag2', 'vocabulary_id': None},
            ('tags', 1, 'vocabulary_id'): None
        }
        errors = []
        context = {'model': model, 'session': model.Session}
        free_tags_only(key, data, errors, context)
        assert len(data) == 2
        assert ('tags', 1, 'vocabulary_id') in data.keys()
        assert ('tags', 1, '__extras') in data.keys()


class MockVocabTagsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IDatasetForm, inherit=True)
    plugins.implements(plugins.IGenshiStreamFilter)

    def is_fallback(self):
        return True

    def package_types(self):
        return ["mock_vocab_tags_plugin"]

    def package_form(self):
        return 'package/new_package_form.html'

    def setup_template_variables(self, context, data_dict=None):
        c.vocab_tags = get_action('tag_list')(context, {'vocabulary_name': TEST_VOCAB_NAME})

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
# so replace with our own implementation here
#
# TODO: this still only handles a single value, fix and test multiple
class Select(paste.fixture.Field):
    def __init__(self, *args, **attrs):
        super(Select, self).__init__(*args, **attrs)
        self.options = []
        self.selectedIndex = None

    def value__set(self, value):
        for i, (option, checked) in enumerate(self.options):
            if option == str(value):
                self.selectedIndex = i
                break
        else:
            raise ValueError(
                "Option %r not found (from %s)"
                % (value, ', '.join(
                [repr(o) for o, c in self.options])))

    def value__get(self):
        if self.selectedIndex is not None:
            return self.options[self.selectedIndex][0]
        else:
            for option, checked in self.options:
                if checked:
                    return option
            else:
                if self.options:
                    return self.options[0][0]
                else:
                    return None

    value = property(value__get, value__set)

paste.fixture.Field.classes['select'] = Select


class TestWUI(WsgiAppCase):
    @classmethod
    def setup_class(cls):
        CreateTestData.create()
        cls.sysadmin_user = model.User.get('testsysadmin')
        cls.dset = model.Package.get('warandpeace')
        cls.tag1_name = 'vocab-tag-1'
        cls.tag2_name = 'vocab-tag-2'

        cls.plugin = MockVocabTagsPlugin()
        plugins.load(cls.plugin)

        # this is a hack so that the plugin is properly registered with
        # the package controller class.
        from ckan.controllers import package as package_controller
        package_controller._default_controller_behaviour = cls.plugin

        # create a test vocab
        params = json.dumps({'name': TEST_VOCAB_NAME})
        extra_environ = {'Authorization' : str(cls.sysadmin_user.apikey)}
        response = cls.app.post('/api/action/vocabulary_create', params=params,
                                extra_environ=extra_environ)
        assert json.loads(response.body)['success']

    @classmethod
    def teardown_class(cls):
        plugins.unload(cls.plugin)
        model.repo.rebuild_db()

    def _get_vocab_id(self, vocab_name):
        params = json.dumps({'name': vocab_name})
        response = self.app.post('/api/action/vocabulary_show', params=params)
        assert json.loads(response.body)['success']
        return json.loads(response.body)['result']['id']

    def _add_vocab_tag(self, vocab_id, tag_name):
        params = json.dumps({'name': tag_name, 'vocabulary_id': vocab_id})
        extra_environ = {'Authorization' : str(self.sysadmin_user.apikey)}
        response = self.app.post('/api/action/tag_create', params=params,
                                 extra_environ=extra_environ)
        assert json.loads(response.body)['success']

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

        # TODO: should really be able to delete a tag with tag name and vocab ID,
        # update tag_delete then change this
        params = json.dumps({'tag_name': tag_name, 'vocabulary_name': TEST_VOCAB_NAME})
        extra_environ = {'Authorization' : str(self.sysadmin_user.apikey)}
        response = self.app.post('/api/action/tag_delete', params=params,
                                 extra_environ=extra_environ)
        assert json.loads(response.body)['success']

    def test_01_dataset_view(self):
        vocab_id = self._get_vocab_id(TEST_VOCAB_NAME)
        self._add_vocab_tag(vocab_id, self.tag1_name)
        self._add_vocab_tag_to_dataset(self.dset.id, vocab_id, self.tag1_name)
        response = self.app.get(h.url_for(controller='package', action='read', id=self.dset.id))
        assert self.tag1_name in response.body
        self._remove_vocab_tags(self.dset.id, vocab_id, self.tag1_name)

    def test_02_dataset_edit_add_vocab_tag(self):
        vocab_id = self._get_vocab_id(TEST_VOCAB_NAME)
        self._add_vocab_tag(vocab_id, self.tag1_name)
        self._add_vocab_tag(vocab_id, self.tag2_name)
        url = h.url_for(controller='package', action='edit', id=self.dset.id)
        response = self.app.get(url)
        fv = response.forms['dataset-edit']
        fv['vocab_tags'] = self.tag2_name
        response = fv.submit('save')
        response = response.follow()
        assert not self.tag1_name in response.body
        assert self.tag2_name in response.body
        self._remove_vocab_tags(self.dset.id, vocab_id, self.tag1_name)
        self._remove_vocab_tags(self.dset.id, vocab_id, self.tag2_name)

