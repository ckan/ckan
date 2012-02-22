import ckan
from ckan.plugins import SingletonPlugin, implements, IPackageController
import sqlalchemy

class MultilingualDataset(SingletonPlugin):
    implements(IPackageController, inherit=True)

    def before_index(self, search_params):
        return search_params

    def before_search(self, search_params):
        return search_params

    def before_view(self, data_dict):
        if data_dict.has_key('tags'):
            tag_names = [tag['name'] for tag in data_dict['tags']]
            translations = ckan.logic.action.get.term_translation_show(
                    {'model': ckan.model},
                    {'terms': tag_names, 'lang_code': 'de'})
            for translation in translations:
                for tag in data_dict['tags']:
                    if tag['name'] == translation['term']:
                        tag['display name'] = translation['term_translation']
        return data_dict
        
class MultilingualGroup(SingletonPlugin):
    implements(IPackageController, inherit=True)

    def before_view(self, data_dict):
        return data_dict
