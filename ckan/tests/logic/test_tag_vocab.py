import json
from pylons import request, tmpl_context as c
from genshi.input import HTML
from genshi.filters import Transformer
from ckan import model
from ckan.logic.converters import convert_to_tags, convert_from_tags, free_tags_only
from ckan.lib.navl.dictization_functions import unflatten
from ckan.lib.create_test_data import CreateTestData
import ckan.lib.helpers as h
from ckan import plugins
from ckan.tests import WsgiAppCase

class TestConverters(object):
    @classmethod
    def setup_class(cls):
        # create a new vocabulary
        cls.vocab = model.Vocabulary('test-vocab') 
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

    def setup_template_variables(self, context, data_dict=None):
        # c.vocab_tags = get_action('tag_list')(context, {'vocabulary_name': self.vocab_name})
        pass

    def form_to_db_schema(self):
        # schema = package_form_schema()
        # schema.update({
        #     'vocab_tags': [ignore_missing, convert_to_tags(self.vocab_name)],
        # })
        # return schema
        pass

    def db_to_form_schema(self):
        # schema = package_form_schema()
        # schema.update({
        #     'tags': {
        #         '__extras': [keep_extras, free_tags_only]
        #     },
        #     'vocab_tags_selected': [convert_from_tags(self.vocab_name), ignore_missing],
        # })
        # return schema
        pass

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
        return stream


class TestWUI(WsgiAppCase):
    @classmethod
    def setup_class(cls):
        CreateTestData.create()
        cls.sysadmin_user = model.User.get('testsysadmin')
        cls.dset = model.Package.get('warandpeace')
        cls.vocab_name = 'vocab'
        cls.tag_name = 'vocab-tag'

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def _create_vocabulary(self, vocab_name):
        params = json.dumps({'name': vocab_name})
        extra_environ = {'Authorization' : str(self.sysadmin_user.apikey)}
        response = self.app.post('/api/action/vocabulary_create', params=params,
                                 extra_environ=extra_environ)
        assert json.loads(response.body)['success']
        return json.loads(response.body)['result']['id']

    def _add_vocab_tag(self, vocab_id, tag_name):
        params = json.dumps({'name': tag_name, 'vocabulary_id': vocab_id})
        extra_environ = {'Authorization' : str(self.sysadmin_user.apikey)}
        response = self.app.post('/api/action/tag_create', params=params,
                                 extra_environ=extra_environ)
        assert response.json['success']

    def _add_vocab_tag_to_dataset(self, dataset_id, vocab_id, tag_name):
        params = json.dumps({'id': dataset_id})
        response = self.app.post('/api/action/package_show', params=params)
        dataset = json.loads(response.body)['result']
        dataset['tags'].append({'name': tag_name, 'vocabulary_id': vocab_id})
        params = json.dumps(dataset)
        response = self.app.post('/api/action/package_update', params=params,
                                 extra_environ={'Authorization': str(self.sysadmin_user.apikey)})
        assert response.json['success']

    def test_01_dataset_view(self):
        plugin = MockVocabTagsPlugin()
        plugins.load(plugin)
        vocab_id = self._create_vocabulary(self.vocab_name)
        self._add_vocab_tag(vocab_id, self.tag_name)
        self._add_vocab_tag_to_dataset(self.dset.id, vocab_id, self.tag_name)
        response = self.app.get(h.url_for(controller='package', action='read', id=self.dset.id))
        assert self.vocab_name in response.body


