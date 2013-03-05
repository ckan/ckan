# -*- coding: utf-8 -*-
import ckan.lib.datapreview as datapreview


class TestDataPreview():
    def test_compare_domains(self):
        ''' see https://en.wikipedia.org/wiki/Same_origin_policy
        '''
        comp = datapreview.compare_domains
        assert comp(['http://www.okfn.org', 'http://www.okfn.org']) is True
        assert comp(['http://www.okfn.org', 'http://www.okfn.org', 'http://www.okfn.org']) is True
        assert comp(['http://www.OKFN.org', 'http://www.okfn.org', 'http://www.okfn.org/test/foo.html']) is True
        assert comp(['http://okfn.org', 'http://okfn.org']) is True
        assert comp(['www.okfn.org', 'http://www.okfn.org']) is True
        assert comp(['//www.okfn.org', 'http://www.okfn.org']) is True

        assert comp(['http://www.okfn.org', 'https://www.okfn.org']) is False
        assert comp(['http://www.okfn.org:80', 'http://www.okfn.org:81']) is False
        assert comp(['http://www.okfn.org', 'http://www.okfn.de']) is False
        assert comp(['http://de.okfn.org', 'http://www.okfn.org']) is False

        assert comp(['http://de.okfn.org', 'http:www.foo.com']) is False

        assert comp(['httpö://wöwöwö.ckan.dö', 'www.ckän.örg']) is False
        assert comp(['www.ckän.örg', 'www.ckän.örg']) is True

        # Wrong URL. Makes urlparse choke
        assert comp(['http://Server=cda3; Service=sde:sqlserver:cda3; Database=NationalDatasets; User=sde; Version=sde.DEFAULT', 'http://www.okf.org']) is False
