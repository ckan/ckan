from ckan.plugins import SingletonPlugin, implements, IPackageController

class MultilingualDataset(SingletonPlugin):
    implements(IPackageController, inherit=True)

    def before_index(self, search_params):
        return search_params

    def before_search(self, search_params):
        return search_params

    def before_view(self, data_dict):
        return data_dict
        
        
class MultilingualGroup(SingletonPlugin):
    implements(IPackageController, inherit=True)

    def before_view(self, data_dict):
        return data_dict
