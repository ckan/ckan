from ckan import model
from ckan.logic.converters import convert_to_tags
from ckan.lib.navl.dictization_functions import unflatten

class TestConverters:
    def test_convert_to_tags(self):
        def convert(tag_string, vocab):
            key = 'vocab_tag_string'
            data = {key: tag_string}
            errors = []
            context = {'model': model, 'session': model.Session}
            convert_to_tags('vocab')(key, data, errors, context)
            del data[key]
            return data

        data = unflatten(convert('tag1, tag2', 'vocab'))
        for tag in data['tags']:
            assert tag['name'] in ['tag1', 'tag2']
            assert tag['vocabulary'] == 'vocab'

