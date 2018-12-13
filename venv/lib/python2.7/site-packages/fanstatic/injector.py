import webob
import webob.dec

from fanstatic.config import convert_config
import fanstatic

CONTENT_TYPES = ['text/html', 'text/xml', 'application/xhtml+xml']

class Injector(object):
    """Fanstatic injector WSGI framework component.

    This WSGI component takes care of injecting the proper resource
    inclusions into HTML when needed.

    This WSGI component is used automatically by the
    :py:func:`Fanstatic` WSGI framework component, but can also be
    used independently if you need more control.

    :param app: The WSGI app to wrap with the injector.

    :param ``**config``: Optional keyword arguments. These are passed
      to :py:class:`NeededResources` when it is constructed. It also
      makes sure that when initialized, it isn't given any
      configuration parameters that cannot be passed to
      ``NeededResources``.
    """
    def __init__(self, app, **config):
        self.app = app

        # this is just to give useful feedback early on
        fanstatic.NeededResources(**config)

        self.config = config

    @webob.dec.wsgify
    def __call__(self, request):
        # We only continue if the request method is appropriate.
        if not request.method in ['GET', 'POST']:
            return request.get_response(self.app)

        # Initialize a needed resources object.
        # XXX this will set the needed on the thread local data, even
        # if the wrapped framework only gets the needed from the WSGI
        # environ.
        needed = fanstatic.init_needed(
            script_name=request.environ.get('SCRIPT_NAME'), **self.config)

        # Make sure the needed resource object is put in the WSGI
        # environment as well, for frameworks that choose to use it
        # from there.
        request.environ[fanstatic.NEEDED] = needed

        # Get the response from the wrapped application:
        response = request.get_response(self.app)

        # We only continue if the content-type is appropriate.
        if not (response.content_type and
                response.content_type.lower() in CONTENT_TYPES):
            # Clean up after our behinds.
            fanstatic.del_needed()
            return response

        # The wrapped application may have `needed` resources.
        if needed.has_resources():
            result = needed.render_topbottom_into_html(response.body)
            # Reset the body...
            response.body = ''
            # And write the result. The `write` method handles unicode results.
            response.write(result)

        # Clean up after our behinds.
        fanstatic.del_needed()

        return response


def make_injector(app, global_config, **local_config):
    local_config = convert_config(local_config)
    return Injector(app, **local_config)
