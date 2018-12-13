# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
from paste.deploy.converters import aslist, asbool
from paste.script.serve import ensure_port_cleanup
import warnings

def warn(name, stacklevel=3):
    # Deprecated 2007-12-17
    warnings.warn(
        'The egg:PasteScript#flup_%s entry point is deprecated; please use egg:Flup#%s instead'
        % (name, name),
        DeprecationWarning, stacklevel=stacklevel)

def run_ajp_thread(wsgi_app, global_conf,
                   scriptName='', host='localhost', port='8009',
                   allowedServers='127.0.0.1'):
    import flup.server.ajp
    warn('ajp_thread')
    addr = (host, int(port))
    ensure_port_cleanup([addr])
    s = flup.server.ajp.WSGIServer(
        wsgi_app,
        scriptName=scriptName,
        bindAddress=addr,
        allowedServers=aslist(allowedServers),
        )
    s.run()

def run_ajp_fork(wsgi_app, global_conf,
                 scriptName='', host='localhost', port='8009',
                 allowedServers='127.0.0.1'):
    import flup.server.ajp_fork
    warn('ajp_fork')
    addr = (host, int(port))
    ensure_port_cleanup([addr])
    s = flup.server.ajp_fork.WSGIServer(
        wsgi_app,
        scriptName=scriptName,
        bindAddress=addr,
        allowedServers=aslist(allowedServers),
        )
    s.run()

def run_fcgi_thread(wsgi_app, global_conf,
                    host=None, port=None,
                    socket=None, umask=None,
                    multiplexed=False):
    import flup.server.fcgi
    warn('fcgi_thread')
    if socket:
        assert host is None and port is None
        sock = socket
    elif host:
        assert host is not None and port is not None
        sock = (host, int(port))
        ensure_port_cleanup([sock])
    else:
        sock = None
    if umask is not None:
        umask = int(umask)
    s = flup.server.fcgi.WSGIServer(
        wsgi_app,
        bindAddress=sock, umask=umask,
        multiplexed=asbool(multiplexed))
    s.run()

def run_fcgi_fork(wsgi_app, global_conf,
                  host=None, port=None,
                  socket=None, umask=None,
                  multiplexed=False):
    import flup.server.fcgi_fork
    warn('fcgi_fork')
    if socket:
        assert host is None and port is None
        sock = socket
    elif host:
        assert host is not None and port is not None
        sock = (host, int(port))
        ensure_port_cleanup([sock])
    else:
        sock = None
    if umask is not None:
        umask = int(umask)
    s = flup.server.fcgi_fork.WSGIServer(
        wsgi_app,
        bindAddress=sock, umask=umask,
        multiplexed=asbool(multiplexed))
    s.run()

def run_scgi_thread(wsgi_app, global_conf,
                    scriptName='', host='localhost', port='4000',
                    allowedServers='127.0.0.1'):
    import flup.server.scgi
    warn('scgi_thread')
    addr = (host, int(port))
    ensure_port_cleanup([addr])
    s = flup.server.scgi.WSGIServer(
        wsgi_app,
        scriptName=scriptName,
        bindAddress=addr,
        allowedServers=aslist(allowedServers),
        )
    s.run()

def run_scgi_fork(wsgi_app, global_conf,
                  scriptName='', host='localhost', port='4000',
                  allowedServers='127.0.0.1'):
    import flup.server.scgi_fork
    warn('scgi_fork')
    addr = (host, int(port))
    ensure_port_cleanup([addr])
    s = flup.server.scgi_fork.WSGIServer(
        wsgi_app,
        scriptName=scriptName,
        bindAddress=addr,
        allowedServers=aslist(allowedServers),
        )
    s.run()

