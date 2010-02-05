import surf

DOMAIN = 'http://ckan.net'
CKAN_NAMESPACE = 'http://ckan.net/#'
CKAN_SUBJECT_BASE = DOMAIN + '/package/'

class RdfExporter(object):
    def __init__(self):
        surf.ns.register(ckan=CKAN_NAMESPACE)
        surf.ns.register(dc='http://purl.org/dc/elements/1.1/') # old, allows literals
        #surf.ns.register(dc='http://purl.org/dc/terms/') # new one

    def export_package(self, pkg):
        assert isinstance(pkg, dict)
        
        store = surf.Store(reader='rdflib',
                           writer='rdflib',
                           rdflib_store='IOMemory')

        self._rdf_session = surf.Session(store)
        
        PackageRdf = self._web_resource(surf.ns.CKAN['Package'])[0]

        pkg_rdf = PackageRdf(subject=CKAN_SUBJECT_BASE + pkg['name'])

        pkg_rdf.foaf_isPrimaryTopicOf = self._web_resource(DOMAIN + '/package/read/%s' % pkg['name'])


        if pkg['download_url']:
            pkg_rdf.ckan_downloadUrl = self._web_resource(pkg['download_url'])

        if pkg['title']:
            pkg_rdf.dc_title = pkg['title']

        if pkg['url']:
            pkg_rdf.foaf_homepage = self._web_resource(pkg['url'])

        if pkg['tags']:
            pkg_rdf.dc_subject = pkg['tags']

        if pkg['author'] or pkg['author_email']:
##            pkg_rdf.dc_creator = pkg['author'].strip()
##            if pkg['author_email']:
##                pkg_rdf.dc_creator = [pkg['author'].strip(), self._web_resource('mailto:' + pkg['author_email'])]
            pkg_rdf.dc_creator = ((pkg['author'] or '') + ' ' + (pkg['author_email'] or '')).strip()

        if pkg['maintainer'] or pkg['maintainer_email']:
            pkg_rdf.dc_contributor = ((pkg['maintainer'] or '') + ' ' + (pkg['maintainer_email'] or '')).strip()

        if pkg['license']:
            pkg_rdf.dc_rights = pkg['license']

        if pkg['notes']:
            pkg_rdf.dc_description = pkg['notes']

        self._rdf_session.commit()

        return pkg_rdf.serialize()
    
    def _web_resource(self, url):
        # cope with multiple urls in string
        url = url.replace(',', ' ')
        urls = url.split()

        url_classes = []
        for url in urls:
            try:
                url_classes.append(self._rdf_session.get_class(url))
            except ValueError, e:
                url_classes.append(url)

        return url_classes

