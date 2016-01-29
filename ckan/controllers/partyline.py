from pylons.controllers import WSGIController

import ckan.lib.base as base
from ckan.common import request, g

from wsgi_party import WSGIParty, HighAndDry

import logging
log = logging.getLogger(__name__)


class PartylineController(WSGIController):

    '''Handle requests from the WSGI stack 'partyline'. Most importantly,
    answers the question, 'can you handle this url?'. '''

    def __init__(self, *args, **kwargs):
        super(PartylineController, self).__init__(*args, **kwargs)
        self.app = None  # A reference to the main pylons app.

    def join_party(self):
        if hasattr(g, 'partyline_connected'):
            base.abort(404)
        self.partyline = request.environ.get(WSGIParty.partyline_key)
        self.app = request.environ.get('partyline_handling_app')
        self.partyline.connect('can_handle_url', self._can_handle_url)
        setattr(g, 'partyline_connected', True)
        return 'ok'

    def _can_handle_url(self, payload):
        if payload != '/flask_hello':
            return (True, self.app)
        else:
            raise HighAndDry()
