from nose.tools import assert_equal
from pylons.test import pylonsapp
import paste.fixture

from routes import url_for as url_for


# This is stolen from the old tests and should probably go in __init__.py
# if it is what we want.
class WsgiAppCase(object):
    wsgiapp = pylonsapp
    assert wsgiapp, 'You need to run nose with --with-pylons'
    # Either that, or this file got imported somehow before the tests started
    # running, meaning the pylonsapp wasn't setup yet (which is done in
    # pylons.test.py:begin())
    app = paste.fixture.TestApp(wsgiapp)


class TestUtil(WsgiAppCase):
    def test_redirect_ok(self):
        response = self.app.get(
            url=url_for(controller='util', action='redirect'),
            params={'url': '/dataset'},
            status=302,
        )
        assert_equal(response.header_dict.get('Location'),
                     'http://localhost/dataset')

    def test_redirect_external(self):
        response = self.app.get(
            url=url_for(controller='util', action='redirect'),
            params={'url': 'http://nastysite.com'},
            status=403,
        )

    def test_redirect_no_params(self):
        response = self.app.get(
            url=url_for(controller='util', action='redirect'),
            params={},
            status=400,
        )

    def test_redirect_no_params_2(self):
        response = self.app.get(
            url=url_for(controller='util', action='redirect'),
            params={'url': ''},
            status=400,
        )
