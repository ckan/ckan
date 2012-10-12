import json
import paste.fixture
from ckan import model
from ckan.lib.create_test_data import CreateTestData
import ckan.lib.helpers as h
from ckan.tests import WsgiAppCase
# ensure that test_tag_vocab_plugin is added as a plugin in the testing .ini file
from ckanext.test_tag_vocab_plugin import MockVocabTagsPlugin

TEST_VOCAB_NAME = 'test-vocab'



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
        MockVocabTagsPlugin().set_active(True)
        CreateTestData.create(package_type='mock_vocab_tags_plugin')
        cls.sysadmin_user = model.User.get('testsysadmin')
        cls.dset = model.Package.get('warandpeace')
        cls.tag1_name = 'vocab-tag-1'
        cls.tag2_name = 'vocab-tag-2'

        # use our custom select class for this test suite
        cls.old_select = paste.fixture.Field.classes['select']
        paste.fixture.Field.classes['select'] = Select

        # create a test vocab
        params = json.dumps({'name': TEST_VOCAB_NAME})
        extra_environ = {'Authorization' : str(cls.sysadmin_user.apikey)}
        cls.extra_environ = {'Authorization' : str(cls.sysadmin_user.apikey)}
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
        MockVocabTagsPlugin().set_active(False)
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
        dataset['tags'] = []
        dataset['tags'].append({'name': tag_name, 'vocabulary_id': vocab_id})
        params = json.dumps(dataset)
        response = self.app.post('/api/action/package_update', params=params,
                                 extra_environ={'Authorization': str(self.sysadmin_user.apikey)})
        assert json.loads(response.body)['success']

    def _remove_vocab_tags(self, dataset_id, vocab_id, tag_name):
        params = json.dumps({'id': dataset_id})
        response = self.app.post('/api/action/package_show', params=params)
        dataset = json.loads(response.body)['result']
        dataset['vocab_tag_selected'] = []
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
        response = self.app.get(url, extra_environ=self.extra_environ)
        fv = response.forms['dataset-edit']
        fv = Form(fv.response, fv.text)
        fv['vocab_tags'] = [self.tag2_name]
        response = fv.submit('save', extra_environ=self.extra_environ)
        response = response.follow()
        assert not self.tag1_name in response.body
        assert self.tag2_name in response.body
        self._remove_vocab_tags(self.dset.id, vocab_id, self.tag1_name)
        self._remove_vocab_tags(self.dset.id, vocab_id, self.tag2_name)

    def test_02_dataset_edit_add_free_and_vocab_tags_then_edit_again(self):
        vocab_id = self._get_vocab_id(TEST_VOCAB_NAME)
        url = h.url_for(controller='package', action='edit', id=self.dset.id)
        response = self.app.get(url, extra_environ=self.extra_environ)
        fv = response.forms['dataset-edit']
        fv = Form(fv.response, fv.text)

        # Add a free tag with a space in its name.
        fv['tag_string'] = 'water quality'

        # Add a vocab tag.
        fv['vocab_tags'] = [self.tag2_name]

        # Save the dataset and visit the page again
        response = fv.submit('save', extra_environ=self.extra_environ)
        response = response.follow()
        assert not self.tag1_name in response.body
        assert self.tag2_name in response.body
        url = h.url_for(controller='package', action='edit', id=self.dset.id)
        response = self.app.get(url, extra_environ=self.extra_environ)
        fv = response.forms['dataset-edit']
        fv = Form(fv.response, fv.text)
        assert fv['vocab_tags'].value == [self.tag2_name], fv['vocab_tags'].value
        self._remove_vocab_tags(self.dset.id, vocab_id, self.tag2_name)

    def test_03_dataset_edit_remove_vocab_tag(self):
        vocab_id = self._get_vocab_id(TEST_VOCAB_NAME)
        self._add_vocab_tag_to_dataset(self.dset.id, vocab_id, self.tag1_name)
        url = h.url_for(controller='package', action='edit', id=self.dset.id)
        response = self.app.get(url, extra_environ=self.extra_environ)
        fv = response.forms['dataset-edit']
        fv = Form(fv.response, fv.text)
        fv['vocab_tags'] = []
        response = fv.submit('save', extra_environ=self.extra_environ)
        response = response.follow()
        assert not self.tag1_name in response.body
        self._remove_vocab_tags(self.dset.id, vocab_id, self.tag1_name)

    def test_04_dataset_edit_change_vocab_tag(self):
        vocab_id = self._get_vocab_id(TEST_VOCAB_NAME)
        self._add_vocab_tag_to_dataset(self.dset.id, vocab_id, self.tag1_name)
        url = h.url_for(controller='package', action='edit', id=self.dset.id)
        response = self.app.get(url, extra_environ=self.extra_environ)
        fv = response.forms['dataset-edit']
        fv = Form(fv.response, fv.text)
        fv['vocab_tags'] = [self.tag2_name]
        response = fv.submit('save', extra_environ=self.extra_environ)
        response = response.follow()
        assert not self.tag1_name in response.body
        assert self.tag2_name in response.body
        self._remove_vocab_tags(self.dset.id, vocab_id, self.tag2_name)

    def test_05_dataset_edit_add_multiple_vocab_tags(self):
        vocab_id = self._get_vocab_id(TEST_VOCAB_NAME)
        url = h.url_for(controller='package', action='edit', id=self.dset.id)
        response = self.app.get(url, extra_environ=self.extra_environ)
        fv = response.forms['dataset-edit']
        fv = Form(fv.response, fv.text)
        fv['vocab_tags'] = [self.tag1_name, self.tag2_name]
        response = fv.submit('save', extra_environ=self.extra_environ)
        response = response.follow()
        assert self.tag1_name in response.body
        assert self.tag2_name in response.body
        self._remove_vocab_tags(self.dset.id, vocab_id, self.tag1_name)
        self._remove_vocab_tags(self.dset.id, vocab_id, self.tag2_name)

