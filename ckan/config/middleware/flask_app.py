# encoding: utf-8

from flask import Flask
from flask import abort as flask_abort
from flask import request as flask_request
from flask import _request_ctx_stack
from werkzeug.exceptions import HTTPException

from wsgi_party import WSGIParty, HighAndDry


import logging
log = logging.getLogger(__name__)


def make_flask_stack(conf, **app_conf):
    """ This has to pass the flask app through all the same middleware that
    Pylons used """

    app = CKANFlask(__name__)

    # Update Flask config with the CKAN values
    app.config.update(conf)
    app.config.update(app_conf)

    @app.route('/hello', methods=['GET'])
    def hello_world():
        return 'Hello World, this is served by Flask'

    @app.route('/hello', methods=['POST'])
    def hello_world_post():
        return 'Hello World, this was posted to Flask'

    return app


class CKANFlask(Flask):

    '''Extend the Flask class with a special view to join the 'partyline'
    established by AskAppDispatcherMiddleware.

    Also provide a 'can_handle_request' method.
    '''

    def __init__(self, import_name, *args, **kwargs):
        super(CKANFlask, self).__init__(import_name, *args, **kwargs)
        self.add_url_rule('/__invite__/', endpoint='partyline',
                          view_func=self.join_party)
        self.partyline = None
        self.partyline_connected = False
        self.invitation_context = None
        self.app_name = None  # A label for the app handling this request
                              # (this app).

    def join_party(self, request=flask_request):
        # Bootstrap, turn the view function into a 404 after registering.
        if self.partyline_connected:
            # This route does not exist at the HTTP level.
            flask_abort(404)
        self.invitation_context = _request_ctx_stack.top
        self.partyline = request.environ.get(WSGIParty.partyline_key)
        self.app_name = request.environ.get('partyline_handling_app')
        self.partyline.connect('can_handle_request', self.can_handle_request)
        self.partyline_connected = True
        return 'ok'

    def can_handle_request(self, environ):
        '''
        Decides whether it can handle a request with the Flask app by
        matching the request environ against the route mapper

        Returns (True, 'flask_app') if this is the case.
        '''

        # TODO: identify matching urls as core or extension. This will depend
        # on how we setup routing in Flask

        urls = self.url_map.bind_to_environ(environ)
        try:
            endpoint, args = urls.match()
            log.debug('Flask route match, endpoint: {0}, args: {1}'.format(
                endpoint, args))
            return (True, self.app_name)
        except HTTPException:
            raise HighAndDry()
