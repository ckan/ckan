import ckan.logic

def update_organization_name_on_datasets(org_id, page_size=100):
    """
    Updates the SOLR indexes for an organization after it is renamed
    
    :param org_id: the ID of the organization that has changed its name
    :type id: string


    :param page_size: the maximum number of datasets from package_search in each request; will paginate if total results are greater
    :type id: int
    """
    packages = ckan.logic.action.get.package_search(fq="owner_org:" + org_id, rows=page_size)

    for dataset in packages.results:
        ckan.lib.search.rebuild(package_id=dataset.id)

    if packages.count > page_size:
        r = page_size
        while r < packages.count:
            p2 = ckan.logic.action.get.package_search(fq="owner_org:" + org_id, rows=page_size, start=r)
            for dataset in p2.results:
                ckan.lib.search.rebuild(package_id=dataset.id)
            r += page_size