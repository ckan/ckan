from pylons.controllers import WSGIController
from pylons import config

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
        self.app_name = request.environ.get('partyline_handling_app')
        self.partyline.connect('can_handle_request', self._can_handle_request)
        setattr(g, 'partyline_connected', True)
        return 'ok'

    def _can_handle_request(self, environ):
        '''
        Decides whether it can handle a request with the Pylons app by
        matching the request environ against the route mapper

        Returns (True, 'pylons_app') if this is the case.

        NOTE: There is currently a catch all route for GET requests to
        point arbitrary urls to templates with the same name:

            map.connect('/*url', controller='template', action='view')

        This means that this function will match all GET requests. This
        does not cause issues as the Pylons core routes are the last to
        take precedence so the current behaviour is kept, but it's worth
        keeping in mind.
        '''

        pylons_mapper = config['routes.map']
        match = pylons_mapper.match(environ=environ)
        if match:
            log.debug('Pylons route match: {0}'.format(match))
            return (True, self.app_name)
        else:
            raise HighAndDry()
