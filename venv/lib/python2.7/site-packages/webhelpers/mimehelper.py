"""MIME Type helpers

This helper depends on the WebOb package, and has optional Pylons support.
"""
import mimetypes

class MIMETypes(object):
    """MIMETypes registration mapping
    
    The MIMETypes object class provides a single point to hold onto all
    the registered mimetypes, and their association extensions. It's
    used by the mimetypes method to determine the appropriate content
    type to return to a client.
    
    """
    aliases = {}
    
    def init(cls):
        """Loads a default mapping of extensions and mimetypes
        
        These are suitable for most web applications by default. 
        Additional types can be added by using the mimetypes module.
        
        """
        mimetypes.init()
    init = classmethod(init)
    
    def add_alias(cls, alias, mimetype):
        """Create a MIMEType alias to a full mimetype.

        Examples:

        - ``add_alias('html', 'text/html')``
        - ``add_alias('xml', 'application/xml')``

        An ``alias`` may not contain the ``/`` character.

        """
        if '/' in alias:
            raise ValueError("MIMEType aliases may not contain '/'")
        cls.aliases[alias] = mimetype
    add_alias = classmethod(add_alias)
    
    def __init__(self, environ):
        """``environ`` is the WSGI environment of the current request."""
        self.env = environ
    
    def _set_response_content_type(self, mimetype):
        if 'pylons.pylons' in self.env:
            self.env['pylons.pylons'].response.content_type = mimetype
        return mimetype
        
    def mimetype(self, content_type):
        """Check the PATH_INFO of the current request and client's HTTP Accept 
        to attempt to use the appropriate mime-type.

        If a content-type is matched, return the appropriate response
        content type, and if running under Pylons, set the response content
        type directly. If a content-type is not matched, return ``False``.
                
        This works best with URLs that end in extensions that differentiate
        content-type. Examples: ``http://example.com/example``, 
        ``http://example.com/example.xml``, ``http://example.com/example.csv``
                
        Since browsers generally allow for any content-type, but should be
        sent HTML when possible, the html mimetype check should always come
        first, as shown in the example below.
        
        Example::
        
            # some code likely in environment.py
            MIMETypes.init()
            MIMETypes.add_alias('html', 'text/html')
            MIMETypes.add_alias('xml', 'application/xml')
            MIMETypes.add_alias('csv', 'text/csv')
            
            # code in a Pylons controller
            def someaction(self):
                # prepare a bunch of data
                # ......
                
                # prepare MIMETypes object
                m = MIMETypes(request.environ)
                
                if m.mimetype('html'):
                    return render('/some/template.html')
                elif m.mimetype('atom'):
                    return render('/some/xml_template.xml')
                elif m.mimetype('csv'):
                    # write the data to a csv file
                    return csvfile
                else:
                    abort(404)

            # Code in a non-Pylons controller.
            m = MIMETypes(environ)
            response_type = m.mimetype('html')
            # ``response_type`` is a MIME type or ``False``.
        """
        import webob

        if content_type in MIMETypes.aliases:
            content_type = MIMETypes.aliases[content_type]
        path = self.env['PATH_INFO']
        guess_from_url = mimetypes.guess_type(path)[0]
        possible_from_accept_header = None
        has_extension = False
        if len(path.split('/')) > 1:
            last_part = path.split('/')[-1]
            if '.' in last_part:
                has_extension = True
        if 'HTTP_ACCEPT' in self.env:
            possible_from_accept_header = webob.acceptparse.MIMEAccept('ACCEPT', 
                self.env['HTTP_ACCEPT'])
        if has_extension == False:
            if possible_from_accept_header is None:
                return self._set_response_content_type(content_type)
            elif content_type in possible_from_accept_header:
                return self._set_response_content_type(content_type)
            else:
                return False
        if content_type == guess_from_url:
            # Guessed same mimetype
            return self._set_response_content_type(content_type)
        elif guess_from_url is None and content_type in possible_from_accept_header:
            return self._set_response_content_type(content_type)
        else:
            return False
