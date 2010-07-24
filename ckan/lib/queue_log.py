from pprint import pprint
from async_notifier import AsyncNotifier
from ckan.model.notifier import Notification

SENDER = 'queue_log'
OPERATION = 'hit'
ROUTING_KEY = 'request_log'

SKIP_KEYS = ['beaker.', 'pylons.', 'paste.', 'wsgi.', 'webob.', 'weberror.', 'routes.', 'repoze.', 'wsgiorg.']

class QueueLogMiddleware(AsyncNotifier):
    
    def __init__(self, app):
        self.app = app
        
    def __call__(self, environ, start_response):
        try:
            return self.app(environ, start_response)
        finally:
            req = environ.get('pylons.original_request')
            resp = environ.get('pylons.original_response')
            if req and resp:
                payload = {
                    'req_method': req.method,
                    'req_host': req.host,
                    'req_headers': dict([(k, v) for k, v in req.headers.items()]),
                    'req_path': req.path,
                    'req_params': dict([(k, v) for k, v in req.params.items()]),
                    'req_user_agent': req.user_agent,
                    'req_content_type': req.content_type,
                    'resp_etag': resp.etag,
                    'resp_status': resp.status,
                    'resp_status_code': resp.status_int,
                    'resp_content_type': resp.content_type,
                    'resp_content_encoding': resp.content_encoding,
                }
            else: payload = {}
            notification = Notification(ROUTING_KEY, 
                                        operation=OPERATION, 
                                        payload=payload)
            self.send_asynchronously(SENDER, **notification)