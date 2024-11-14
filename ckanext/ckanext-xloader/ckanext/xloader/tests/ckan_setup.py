try:
    from ckan.tests.pytest_ckan.ckan_setup import *  # noqa
except ImportError:
    import pkg_resources
    from paste.deploy import loadapp
    import sys
    import os

    import pylons
    from pylons.i18n.translation import _get_translator

    def pytest_addoption(parser):
        """Allow using custom config file during tests.
        """
        parser.addoption(u"--ckan-ini", action=u"store")

    def pytest_sessionstart(session):
        """Initialize CKAN environment.
        """
        global pylonsapp
        path = os.getcwd()
        sys.path.insert(0, path)
        pkg_resources.working_set.add_entry(path)
        pylonsapp = loadapp(
            "config:" + session.config.option.ckan_ini, relative_to=path,
        )

        # Initialize a translator for tests that utilize i18n
        translator = _get_translator(pylons.config.get("lang"))
        pylons.translator._push_object(translator)

        class FakeResponse:
            headers = {}  # because render wants to delete Pragma

        pylons.response._push_object(FakeResponse)
