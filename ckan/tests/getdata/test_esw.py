import ckan.model as model
import ckan.getdata.esw as esw


test_data='ckan/tests/getdata/samples/esw.txt'
test_data2='ckan/tests/getdata/samples/data4nr2.csv'

if True:
    CKAN_HOST = 'test.ckan.net'
    API_KEY = u'2d0ba994-e6a7-439b-bb29-9c0cdd660a60'
else:
    CKAN_HOST = 'localhost:5000'
    API_KEY = u'f6afa2d0-2264-48d3-92b8-27f604fa201f'

TEST_PKG_NAMES = ['addgene', 'bams', 'wikipedia3', 'bbc_john_peel_sessions', 'chef_moz']

class TestBasic:
    @classmethod
    def setup_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        self.data = esw.Esw()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()

    def test_load_data(self):
        assert model.Session.query(model.Package).count() == 0
        self.data.load_esw_txt_into_db(test_data)
        assert model.Session.query(model.Package).count() >= 4, model.Session.query(model.Package).count()

    def test_name_munge(self):
        def test_munge(title_field, expected_title, expected_name):
            name, title = self.data._create_name({'Project':title_field})
            assert title == expected_title, 'Got title \'%s\' not \'%s\'' % (title, expected_title)
            assert name == expected_name, 'Got name %s not %s' % (name, expected_name)
        test_munge('[http://www.addgene.org/ Addgene]', 'Addgene', 'addgene')
        test_munge('[http://airports.dataincubator.org/ Airport Data]', 'Airport Data', 'airport_data')
        test_munge('Entrez Gene Extract from [ftp://ftp.ncbi.nlm.nih.gov/gene/DATA/gene_info.gz]', 'Entrez Gene Extract', 'entrez_gene_extract')

    def test_get_link(self):
        def test_munge(before_txt, expected_after_txt):
            after_txt = self.data._get_link(before_txt)
            assert after_txt == expected_after_txt, 'Got text \'%s\' not \'%s\'' % (after_txt, expected_after_txt)
        test_munge('[http://purl.org/hcls/2007/kb-sources/addgene.ttl tab-delimited file]', 'http://purl.org/hcls/2007/kb-sources/addgene.ttl')
        test_munge('[http://doapstore.org/data/dataset_xml.rdf.gz RDF/XML], [http://doapstore.org/data/dataset_n3.rdf.gz N3]', 'http://doapstore.org/data/dataset_xml.rdf.gz, http://doapstore.org/data/dataset_n3.rdf.gz')

    def test_unwiki_link(self):
        def test_munge(before_txt, expected_after_txt):
            after_txt = self.data._unwiki_link(before_txt)
            assert after_txt == expected_after_txt, 'Got text \'%s\' not \'%s\'' % (after_txt, expected_after_txt)
        test_munge('[http://www.few.vu.nl/~aisaac Antoine Isaac] and [http://rameau.bnf.fr Rameau committee]', 'Antoine Isaac <http://www.few.vu.nl/~aisaac>, Rameau committee <http://rameau.bnf.fr>')

class TestLoadIntoDb:
    @classmethod
    def setup_class(self):
        data = esw.Esw()
        data.load_esw_txt_into_db(test_data)

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()

    def test_fields(self):
        names = [pkg.name for pkg in model.Session.query(model.Package).all()]
        print names
        pkgs = []
        for pkg_name in TEST_PKG_NAMES:
            pkg = model.Session.query(model.Package).filter_by(name=unicode(pkg_name)).one()
            pkgs.append(pkg)
        def get_attrib(pkg, attrib):
            if attrib == 'groups':
                return [group.name for group in pkg.groups]
            return getattr(pkg, attrib)
        check_package_data(pkgs, get_attrib)
        
def check_package_data(pkgs, get_):
    assert len(pkgs) == len(TEST_PKG_NAMES)
    for pkg in pkgs:
        assert pkg
    assert get_(pkgs[0], 'title') == 'Addgene', get_(pkgs[0], 'title')
    assert get_(pkgs[1], 'title') == 'BAMS', get_(pkgs[1], 'title')
    assert get_(pkgs[2], 'title') == 'Wikipedia3', get_(pkgs[2], 'title')
    assert not get_(pkgs[0], 'author'), repr(get_(pkgs[0], 'author'))
    assert not get_(pkgs[1], 'author'), get_(pkgs[0], 'author')
    assert get_(pkgs[0], 'url') == 'http://www.addgene.org/', get_(pkgs[0], 'url')
    assert get_(pkgs[1], 'url') == 'http://brancusi.usc.edu/bkms/bamsxml.html', get_(pkgs[1], 'url')
    assert get_(pkgs[0], 'download_url') == 'http://purl.org/hcls/2007/kb-sources/addgene.ttl', get_(pkgs[0], 'download_url')
    assert get_(pkgs[1], 'download_url') == 'http://purl.org/hcls/2007/kb-sources/bams-from-swanson-98-4-23-07.owl', get_(pkgs[1], 'download_url')
    assert 'provided to Science Commons by Addgene' in get_(pkgs[0], 'notes'), get_(pkgs[0], 'notes')
    assert '2009-05-24: File does not exist - hg / Health Care and Life Sciences Interest Group (HCLSIG) / National Institute of Standards and Technology (NIST); released without contract' in get_(pkgs[1], 'notes'), get_(pkgs[1], 'notes')
    assert 'Data exposed: Addgene catalog (tab delimited file)' in get_(pkgs[0], 'notes'), get_(pkgs[0], 'notes')
    assert 'Size of dump and data set: 1.1 MB' in get_(pkgs[0], 'notes'), get_(pkgs[0], 'notes')
    extras = get_(pkgs[0], 'extras')
    assert len(extras) == 0, extras
    def get_tag_set(pkg):
        tag_names = set()
        if hasattr(pkg, 'tags'):
            [tag_names.add(tag.name) for tag in pkg.tags]
        else:
            [tag_names.add(tag) for tag in get_(pkg, 'tags')]
        return tag_names
    tags1 = get_tag_set(pkgs[1])
    tags2 = get_tag_set(pkgs[2])
    assert 'rdf' in tags1, tags1
    assert 'format-rdf' in tags1, tags1
    assert len(tags1) == 4, tags1
    assert 'wikipedia' in tags2, tags2
    def get_license_name(pkg):
        if hasattr(pkg, 'license'):
            license_name = pkg.license.name
        else:
            license_name = model.Session.query(model.License).get(pkg['license_id']).name
        return license_name
    assert get_license_name(pkgs[4]) == u'OKD Compliant::Other', get_license_name(pkgs[4])
    assert get_(pkgs[2], 'groups') == ['semanticweb'], get_(pkgs[2], 'groups')
    assert get_(pkgs[0], 'groups') == ['semanticweb'], get_(pkgs[0], 'groups')

# This has extra external dependencies
# Disable until we find a better way to selectively run tests
__test__ = False


# To run this test, supply a suitable test host and then
# uncomment it.
class _TestLoadViaRest:
    @classmethod
    def setup_class(self):
        import ckanclient
        base_location = 'http://%s/api/rest' % CKAN_HOST
        self.ckan = ckanclient.CkanClient(base_location=base_location, api_key=API_KEY)

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()

    def test_fields(self):
        data = esw.Esw()
        data.load_esw_txt_via_rest(test_data, self.ckan)

        self.ckan.package_register_get()
        names = self.ckan.last_message
        pkgs = []
        for pkg_name in TEST_PKG_NAMES:
            pkg = self.ckan.package_entity_get(unicode(pkg_name))
            pkgs.append(pkg)
        def get_attrib(pkg, attrib):
            return pkg[attrib]
        check_package_data(pkgs, get_attrib)
