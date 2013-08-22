import ckan.plugins as plugins


class ExampleIFacetsPlugin(plugins.SingletonPlugin):
    '''An example IFacets CKAN plugin.

    '''
    plugins.implements(plugins.IFacets, inherit=False)

    def dataset_facets(self, facets_dict, package_type):
        del facets_dict['organization']
        facets_dict['title'] = 'Title'
        return facets_dict

    def group_facets(self, facets_dict, group_type):
        return facets_dict

    def organization_facets(self, facets_dict, organization_type):
        return facets_dict
