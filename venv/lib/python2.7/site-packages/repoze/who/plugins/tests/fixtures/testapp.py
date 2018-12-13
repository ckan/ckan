def tack_environ(environ, msg):
    import pprint
    penv = pprint.pformat(environ)
    return msg + '\n\n' + penv

def deny(start_response, environ, msg):
    ct = 'text/plain'
    msg = tack_environ(environ, msg)
    cl = str(len(msg))
    start_response('401 Unauthorized',
                   [ ('Content-Type', ct),
                   ('Content-Length', cl) ],
                   )

def allow(start_response, environ, msg):
    ct = 'text/plain'
    msg = tack_environ(environ, msg)
    cl = str(len(msg))
    start_response('200 OK',
                   [ ('Content-Type', ct),
                   ('Content-Length', cl) ],
                   )
    return [msg]

def app(environ, start_response):
    path_info = environ['PATH_INFO']
    remote_user = environ.get('REMOTE_USER')
    if path_info.endswith('/shared'):
        if not remote_user:
            return deny(start_response, environ, 'You cant do that')
        else:
            return allow(start_response, environ,
                         'Welcome to the shared area, %s' % remote_user)
    elif path_info.endswith('/admin'):
        if remote_user != 'admin':
            return deny(start_response, environ, 'Only admin can do that')
        else:
            return allow(start_response, environ, 'Hello, admin!')
    elif path_info.endswith('/chris'):
        if remote_user != 'chris':
            return deny(start_response, environ, 'Only chris can do that')
        else:
            return allow(start_response, environ, 'Hello, chris!')
    else:
        return allow(start_response, environ, 'Unprotected page')
    
def make_app(global_config, **kw):
    return app

            
        
            
            
