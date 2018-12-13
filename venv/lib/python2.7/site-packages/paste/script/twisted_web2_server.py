# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
# @@: THIS IS INCOMPLETE!

def run_twisted(wsgi_app, global_conf,
                host='127.0.0.1', port='8080'):
    host = host or None
    import twisted.web2.wsgi
    import twisted.web2.log
    import twisted.web2.channel
    import twisted.web2.server
    import twisted.internet.reactor
    wsgi_resource = twisted.web2.wsgi.WSGIResource(wsgi_app)
    resource = twisted.web2.log.LogWrapperResource(wsgi_resource)
    twisted.web2.log.DefaultCommonAccessLoggingObserver().start()
    site = twisted.web2.server.Site(resource)
    factory = twisted.web2.channel.HTTPFactory(site)
    # --- start reactor for listen port
    twisted.internet.reactor.listenTCP(int(port), factory, interface=host)
    twisted.internet.reactor.run()
