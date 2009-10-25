import surf

import ckan.model as model
import ckan.lib.helpers as h

DOMAIN = 'http://ckan.net'
CKAN_NAMESPACE = 'http://ckan.net/#'
CKAN_SUBJECT_BASE = DOMAIN + '/package/rdf/'

class RdfExporter(object):
    def __init__(self):
        surf.ns.register(ckan=CKAN_NAMESPACE)
        surf.ns.register(dc='http://purl.org/dc/elements/1.1/') # old, allows literals
        #surf.ns.register(dc='http://purl.org/dc/terms/') # new one

    def export_package(self, pkg):
        assert isinstance(pkg, model.Package)
        
        store = surf.Store(reader='rdflib',
                           writer='rdflib',
                           rdflib_store='IOMemory')

        self._rdf_session = surf.Session(store)
        
        PackageRdf = self._web_resource(surf.ns.CKAN['Package'])

        assert pkg
        pkg_rdf = PackageRdf(subject=CKAN_SUBJECT_BASE + pkg.name)

        pkg_rdf.foaf_isPrimaryTopicOf = self._web_resource(DOMAIN + h.url_for(controller='package', action='read', id=pkg.name))


        if pkg.download_url:
            pkg_rdf.ckan_downloadUrl = self._web_resource(pkg.download_url)

        if pkg.title:
            pkg_rdf.dc_title = pkg.title

        if pkg.url:
            pkg_rdf.foaf_homepage = self._web_resource(pkg.url)

        if pkg.tags:
            pkg_rdf.dc_subject = [tag.name for tag in pkg.tags]

        if pkg.author or pkg.author_email:
##            pkg_rdf.dc_creator = pkg.author.strip()
##            if pkg.author_email:
##                pkg_rdf.dc_creator = [pkg.author.strip(), self._web_resource('mailto:' + pkg.author_email)]
            pkg_rdf.dc_creator = (pkg.author + ' ' + pkg.author_email).strip()

        if pkg.maintainer or pkg.maintainer_email:
            pkg_rdf.dc_contributor = (pkg.maintainer + ' ' + pkg.maintainer_email).strip()

        if pkg.license:
            pkg_rdf.dc_rights = pkg.license.name

        if pkg.notes:
            pkg_rdf.dc_description = pkg.notes

        self._rdf_session.commit()

        return pkg_rdf.serialize()
    
    def _web_resource(self, url):
        try:
            return self._rdf_session.get_class(url)
        except ValueError, e:
            return url

