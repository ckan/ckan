import ckan.lib.datapreview as datapreview

class TestDataPreview():
    def test_compare_domains(self):
        ''' see https://en.wikipedia.org/wiki/Same_origin_policy
        '''
        comp = datapreview.compare_domains
        assert comp(['http://www.okfn.org', 'http://www.okfn.org']) == True
        assert comp(['http://www.okfn.org', 'http://www.okfn.org', 'http://www.okfn.org']) == True
        assert comp(['http://www.OKFN.org', 'http://www.okfn.org', 'http://www.okfn.org/test/foo.html']) == True
        assert comp(['http://okfn.org', 'http://okfn.org']) == True
        assert comp(['www.okfn.org', 'http://www.okfn.org']) == True
        assert comp(['//www.okfn.org', 'http://www.okfn.org']) == True

        assert comp(['http://www.okfn.org', 'https://www.okfn.org']) == False
        assert comp(['http://www.okfn.org:80', 'http://www.okfn.org:81']) == False
        assert comp(['http://www.okfn.org', 'http://www.okfn.de']) == False
        assert comp(['http://de.okfn.org', 'http://www.okfn.org']) == False

        assert comp(['http://de.okfn.org', 'http:www.foo.com']) == False
