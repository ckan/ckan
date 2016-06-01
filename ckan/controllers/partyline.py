# encoding: utf-8

from pylons.controllers import WSGIController
from pylons import config

import ckan.lib.base as base
from ckan.common import request

from wsgi_party import WSGIParty, HighAndDry

import logging
log = logging.getLogger(__name__)


class PartylineController(WSGIController):

    '''Handle requests from the WSGI stack 'partyline'. Most importantly,
    answers the question, 'can you handle this url?'. '''

    def __init__(self, *args, **kwargs):
        super(PartylineController, self).__init__(*args, **kwargs)
        self.app_name = None  # A reference to the main pylons app.
        self.partyline_connected = False

    def join_party(self):
        if self.partyline_connected:
            base.abort(404)
        self.partyline = request.environ.get(WSGIParty.partyline_key)
        self.app_name = request.environ.get('partyline_handling_app')
        self.partyline.connect('can_handle_request', self.can_handle_request)
        self.partyline_connected = True
        return 'ok'

    def can_handle_request(self, environ):
        '''
        Decides whether it can handle a request with the Pylons app by
        matching the request environ against the route mapper

        Returns (True, 'pylons_app', origin) if this is the case.

        origin can be either 'core' or 'extension' depending on where
        the route was defined.

        NOTE: There is currently a catch all route for GET requests to
        point arbitrary urls to templates with the same name:

            map.connect('/*url', controller='template', action='view')

        This means that this function will match all GET requests. This
        does not cause issues as the Pylons core routes are the last to
        take precedence so the current behaviour is kept, but it's worth
        keeping in mind.
        '''

        pylons_mapper = config['routes.map']
        match_route = pylons_mapper.routematch(environ=environ)
        if match_route:
            match, route = match_route
            origin = 'core'
            if hasattr(route, '_ckan_core') and not route._ckan_core:
                origin = 'extension'
            log.debug('Pylons route match: {0} Origin: {1}'.format(
                match, origin))
            return (True, self.app_name, origin)
        else:
            raise HighAndDry()
