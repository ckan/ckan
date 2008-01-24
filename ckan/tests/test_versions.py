import inspect

class TestVersions(object):

    def test_pylons(self):
        import pylons
        assert pylons.__version__ == '0.9.6.1'

    def test_sqlobject(self):
        import sqlobject
        assert '-0.7.1-' in sqlobject.__path__[0]

    def test_markdown(self):
        import markdown
        line26 = open(inspect.getsourcefile(markdown)).readlines()[25]
        assert "Version: 1.5" in line26

