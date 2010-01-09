import urllib2
import os

import rdf

TALIS_REALM = 'bigfoot'
TALIS_URI = 'http://api.talis.com/stores/'

class TalisLogin:
    storename = 'ckan-dev1'
    username = 'ckan'
    password = None

    @staticmethod
    def init(storename, username, password):
        TalisLogin.storename = storename
        TalisLogin.username = username
        TalisLogin.password = password

    @staticmethod
    def get_password():
        if TalisLogin.password is None:
            TalisLogin.password = os.environ['TALIS_PASSWORD']
        return TalisLogin.password

    @staticmethod
    def get_username():
        return TalisLogin.username

    @staticmethod
    def get_storename():
        return TalisLogin.storename

class Talis:
    def __init__(self):
        self.rdf = rdf.RdfExporter()

    def get_field_predicate_map(self, store):
        fp_map_base = \
'''
<?xml version="1.0" encoding="utf-8"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#" xmlns:bf="http://schemas.talis.com/2006/bigfoot/configuration#" xmlns:frm="http://schemas.talis.com/2006/frame/schema#" >
  <bf:FieldPredicateMap rdf:about="http://api.talis.com/stores/$(store)s/indexes/default/fpmaps/default">
    %(mapped_properties)s
  </bf:FieldPredicateMap>
</rdf:RDF>
'''

        mapped_property = \
'''
    <frm:mappedDatatypeProperty>
      <rdf:Description rdf:about="http://api.talis.com/stores/$(store)s/indexes/default/fpmaps/default#%(property)s">
        <frm:property rdf:resource="%(namespace)s%(property)s"/>
        <frm:name>%(property)</frm:name>
      </rdf:Description>
    </frm:mappedDatatypeProperty>
'''
        namespaces = {'dc':'http://purl.org/dc/elements/1.1/',
                      'foaf':'http://xmlns.com/foaf/0.1/',
                      'ckan':'http://ckan.net/ns#',
        }
        map = [('isPrimaryTopicOf', 'foaf'),
        ('title', 'dc'),
        ('description', 'dc'),
        ('foaf', 'homepage'),
        ('downloadUrl', 'ckan'),
        ('contributor', 'dc'),
        ('rights', 'dc'),
        ('subject', 'dc'),
        ]

        mapped_properties = []
        for property, ns_abbreviation in map:
            mp = mapped_property % {'namespace':namespaces[ns_abbreviation],
            'property':property}
            mapped_properties.append(mp)
        return fp_map_base % {'mapped_properties':'\n'.join(mapped_properties), 'store': store}

    def post_pkg(self, pkg_dict):
        rdf_xml = self.rdf.export_package(pkg_dict)
        service = '/meta'
        return self.post(service, rdf_xml, with_password=True)
    
    def post(self, service, rdf_xml, with_password=False):
        uri = TALIS_URI + TalisLogin.get_storename() + service
        if with_password:
            talis_password = TalisLogin.get_password()
            talis_username = TalisLogin.get_username()
            authhandler = urllib2.HTTPDigestAuthHandler()
            authhandler.add_password(TALIS_REALM, uri, talis_username, talis_password)
            opener = urllib2.build_opener(authhandler)
            urllib2.install_opener(opener)        
        headers = {"User-Agent":"ckan-rdf", "Content-Type":"application/rdf+xml"}
        request = urllib2.Request(uri, rdf_xml, headers)
        try:
            response = urllib2.urlopen(request)
        except urllib2.HTTPError, arg:
            return arg
        return response.read()

    def get_pkg(self, package_name):
        uri = TALIS_URI + TalisLogin.get_storename() + '/meta?about=%s&output=rdf' % (rdf.CKAN_SUBJECT_BASE + package_name)
        return self.get(uri)
        
    def get_pkg_list(self):
        uri = TALIS_URI + TalisLogin.get_storename() + '/meta?about=%s&output=rdf' % (rdf.CKAN_SUBJECT_BASE)
        return self.get(uri)        

    def get(self, uri):
        headers = {"User-Agent":"ckan-rdf"}
        request = urllib2.Request(uri, None, headers)
        try:
            response = urllib2.urlopen(request)
        except urllib2.HTTPError, arg:
            return arg
        return response.read()
        
    def send_rdf(self, talis_store, username, password):
        import ckan.model as model
        TalisLogin.storename = talis_store
        TalisLogin.username = username
        TalisLogin.password = password

        err = None
        for pkg in model.Session.query(model.Package).all():
            pkg_dict = pkg.as_dict()
            err = self.post_pkg(pkg_dict)
            if err:
                print "error"
                print err
                break
        return err

        

    def dump(self):
        pass
