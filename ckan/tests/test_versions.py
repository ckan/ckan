import inspect

class TestVersions(object):

    def test_pylons(self):
        import pylons
        assert pylons.__version__ == '0.9.6.1'

    def test_sqlobject(self):
        import sqlobject
        # assert '-0.7.1-' in sqlobject.__path__[0]
        # we need to allow above 0.7 (up to 0.10 ...)
        pass

