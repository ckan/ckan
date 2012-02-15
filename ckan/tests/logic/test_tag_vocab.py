from ckan import model
from ckan.logic.converters import convert_to_tags, convert_from_tags, free_tags_only
from ckan.lib.navl.dictization_functions import unflatten

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

