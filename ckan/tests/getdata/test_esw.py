import ckan.model as model
import ckan.getdata.esw as esw

test_data='ckan/tests/getdata/samples/esw.txt'
test_data2='ckan/tests/getdata/samples/data4nr2.csv'

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
        assert model.Package.query.count() == 0
        self.data.load_esw_txt_into_db(test_data)
        assert model.Package.query.count() >= 4, model.Package.query.count()

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

class TestData:
    @classmethod
    def setup_class(self):
        data = esw.Esw()
        data.load_esw_txt_into_db(test_data)

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()

    def test_fields(self):
        names = [pkg.name for pkg in model.Package.query.all()]
        print names
        pkg1 = model.Package.query.filter_by(name=u'addgene').one()
        pkg2 = model.Package.query.filter_by(name=u'bams').one()
        pkg3 = model.Package.query.filter_by(name=u'wikipedia3').one()
        pkg4 = model.Package.query.filter_by(name=u'bbc_john_peel_sessions').one()
        assert pkg1
        assert pkg2
        assert pkg3
        assert pkg1.title == 'Addgene', pkg1.title
        assert pkg2.title == 'BAMS', pkg2.title
        assert pkg3.title == 'Wikipedia3', pkg3.title
        assert pkg1.author == '', pkg1.author
        assert pkg2.author == '', pkg1.author
        assert pkg1.url == 'http://www.addgene.org/', pkg1.url
        assert pkg2.url == 'http://brancusi.usc.edu/bkms/bamsxml.html', pkg2.url
        assert pkg1.download_url == 'http://purl.org/hcls/2007/kb-sources/addgene.ttl', pkg1.download_url
        assert pkg2.download_url == 'http://purl.org/hcls/2007/kb-sources/bams-from-swanson-98-4-23-07.owl', pkg2.download_url
        assert 'provided to Science Commons by Addgene' in pkg1.notes, pkg1.notes
        assert '2009-05-24: File does not exist - hg / Health Care and Life Sciences Interest Group (HCLSIG) / National Institute of Standards and Technology (NIST); released without contract' in pkg2.notes, pkg2.notes
        assert 'Data exposed: Addgene catalog (tab delimited file)' in pkg1.notes, pkg1.notes
        assert 'Size of dump and data set: 1.1 MB' in pkg1.notes, pkg1.notes
        extras = pkg1._extras
        assert len(extras) == 0, extras
        tag_names = set()
        [tag_names.add(tag.name) for tag in pkg.tags]
        assert 'rdf' in tag_names, tag_names
        assert 'format-rdf' in tag_names, tag_names
        assert len(tag_names) == 4

