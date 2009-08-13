import inspect

class TestVersions(object):

    def test_pylons(self):
        import pylons
        assert pylons.__version__[0:5] == '0.9.7'

