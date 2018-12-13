"""The base WSGI XMLRPCController"""
import inspect
import logging
import types
import xmlrpclib

from paste.response import replace_header

from pylons.controllers import WSGIController
from pylons.controllers.util import abort, Response

__all__ = ['XMLRPCController']

log = logging.getLogger(__name__)

XMLRPC_MAPPING = ((basestring, 'string'), (list, 'array'), (bool, 'boolean'),
                  (int, 'int'), (float, 'double'), (dict, 'struct'), 
                  (xmlrpclib.DateTime, 'dateTime.iso8601'),
                  (xmlrpclib.Binary, 'base64'))

def xmlrpc_sig(args):
    """Returns a list of the function signature in string format based on a 
    tuple provided by xmlrpclib."""
    signature = []
    for param in args:
        for type, xml_name in XMLRPC_MAPPING:
            if isinstance(param, type):
                signature.append(xml_name)
                break
    return signature


def xmlrpc_fault(code, message):
    """Convienence method to return a Pylons response XMLRPC Fault"""
    fault = xmlrpclib.Fault(code, message)
    return Response(body=xmlrpclib.dumps(fault, methodresponse=True))


class XMLRPCController(WSGIController):
    """XML-RPC Controller that speaks WSGI
    
    This controller handles XML-RPC responses and complies with the 
    `XML-RPC Specification <http://www.xmlrpc.com/spec>`_ as well as
    the `XML-RPC Introspection
    <http://scripts.incutio.com/xmlrpc/introspection.html>`_ 
    specification.
    
    By default, methods with names containing a dot are translated to
    use an underscore. For example, the `system.methodHelp` is handled
    by the method :meth:`system_methodHelp`.
    
    Methods in the XML-RPC controller will be called with the method
    given in the XMLRPC body. Methods may be annotated with a signature
    attribute to declare the valid arguments and return types.
    
    For example::
        
        class MyXML(XMLRPCController):
            def userstatus(self):
                return 'basic string'
            userstatus.signature = [ ['string'] ]
            
            def userinfo(self, username, age=None):
                user = LookUpUser(username)
                response = {'username':user.name}
                if age and age > 10:
                    response['age'] = age
                return response
            userinfo.signature = [['struct', 'string'],
                                  ['struct', 'string', 'int']]
    
    Since XML-RPC methods can take different sets of data, each set of
    valid arguments is its own list. The first value in the list is the
    type of the return argument. The rest of the arguments are the
    types of the data that must be passed in.
    
    In the last method in the example above, since the method can
    optionally take an integer value both sets of valid parameter lists
    should be provided.
    
    Valid types that can be checked in the signature and their
    corresponding Python types::

        'string' - str
        'array' - list
        'boolean' - bool
        'int' - int
        'double' - float
        'struct' - dict
        'dateTime.iso8601' - xmlrpclib.DateTime
        'base64' - xmlrpclib.Binary
    
    The class variable ``allow_none`` is passed to xmlrpclib.dumps;
    enabling it allows translating ``None`` to XML (an extension to the
    XML-RPC specification)

    .. note::

        Requiring a signature is optional.
    
    """
    allow_none = False
    max_body_length = 4194304

    def _get_method_args(self):
        return self.rpc_kargs

    def __call__(self, environ, start_response):
        """Parse an XMLRPC body for the method, and call it with the
        appropriate arguments"""
        # Pull out the length, return an error if there is no valid
        # length or if the length is larger than the max_body_length.
        log_debug = self._pylons_log_debug
        length = environ.get('CONTENT_LENGTH')
        if length:
            length = int(length)
        else:
            # No valid Content-Length header found
            if log_debug:
                log.debug("No Content-Length found, returning 411 error")
            abort(411)
        if length > self.max_body_length or length == 0:
            if log_debug:
                log.debug("Content-Length larger than max body length. Max: "
                          "%s, Sent: %s. Returning 413 error",
                          self.max_body_length, length)
            abort(413, "XML body too large")

        body = environ['wsgi.input'].read(int(environ['CONTENT_LENGTH']))
        rpc_args, orig_method = xmlrpclib.loads(body)

        method = self._find_method_name(orig_method)
        func = self._find_method(method)
        if not func:
            if log_debug:
                log.debug("Method: %r not found, returning xmlrpc fault",
                          method)
            return xmlrpc_fault(0, "No such method name %r" %
                                method)(environ, start_response)

        # Signature checking for params
        if hasattr(func, 'signature'):
            if log_debug:
                log.debug("Checking XMLRPC argument signature")
            valid_args = False
            params = xmlrpc_sig(rpc_args)
            for sig in func.signature:
                # Next sig if we don't have the same amount of args
                if len(sig)-1 != len(rpc_args):
                    continue

                # If the params match, we're valid
                if params == sig[1:]:
                    valid_args = True
                    break

            if not valid_args:
                if log_debug:
                    log.debug("Bad argument signature recieved, returning "
                              "xmlrpc fault")
                msg = ("Incorrect argument signature. %r recieved does not "
                       "match %r signature for method %r" % \
                           (params, func.signature, orig_method))
                return xmlrpc_fault(0, msg)(environ, start_response)

        # Change the arg list into a keyword dict based off the arg
        # names in the functions definition
        arglist = inspect.getargspec(func)[0][1:]
        kargs = dict(zip(arglist, rpc_args))
        kargs['action'], kargs['environ'] = method, environ
        kargs['start_response'] = start_response
        self.rpc_kargs = kargs
        self._func = func
        
        # Now that we know the method is valid, and the args are valid,
        # we can dispatch control to the default WSGIController
        status = []
        headers = []
        exc_info = []
        def change_content(new_status, new_headers, new_exc_info=None):
            status.append(new_status)
            headers.extend(new_headers)
            exc_info.append(new_exc_info)
        output = WSGIController.__call__(self, environ, change_content)
        output = list(output)
        headers.append(('Content-Length', str(len(output[0]))))
        replace_header(headers, 'Content-Type', 'text/xml')
        start_response(status[0], headers, exc_info[0])
        return output

    def _dispatch_call(self):
        """Dispatch the call to the function chosen by __call__"""
        raw_response = self._inspect_call(self._func)
        if not isinstance(raw_response, xmlrpclib.Fault):
            raw_response = (raw_response,)

        response = xmlrpclib.dumps(raw_response, methodresponse=True,
                                   allow_none=self.allow_none)
        return response

    def _find_method(self, name):
        """Locate a method in the controller by the specified name and
        return it"""
        # Keep private methods private
        if name.startswith('_'):
            if self._pylons_log_debug:
                log.debug("Action starts with _, private action not allowed")
            return

        if self._pylons_log_debug:
            log.debug("Looking for XMLRPC method: %r", name)
        try:
            func = getattr(self, name, None)
        except UnicodeEncodeError:
            return
        if isinstance(func, types.MethodType):
            return func

    def _find_method_name(self, name):
        """Locate a method in the controller by the appropriate name
        
        By default, this translates method names like 
        'system.methodHelp' into 'system_methodHelp'.
        
        """
        return name.replace('.', '_')

    def _publish_method_name(self, name):
        """Translate an internal method name to a publicly viewable one
        
        By default, this translates internal method names like
        'blog_view' into 'blog.view'.
        
        """
        return name.replace('_', '.')

    def system_listMethods(self):
        """Returns a list of XML-RPC methods for this XML-RPC resource"""
        methods = []
        for method in dir(self):
            meth = getattr(self, method)

            if not method.startswith('_') and isinstance(meth,
                                                         types.MethodType):
                methods.append(self._publish_method_name(method))
        return methods
    system_listMethods.signature = [['array']]

    def system_methodSignature(self, name):
        """Returns an array of array's for the valid signatures for a
        method.

        The first value of each array is the return value of the
        method. The result is an array to indicate multiple signatures
        a method may be capable of.
        
        """
        method = self._find_method(self._find_method_name(name))
        if method:
            return getattr(method, 'signature', '')
        else:
            return xmlrpclib.Fault(0, 'No such method name')
    system_methodSignature.signature = [['array', 'string'],
                                        ['string', 'string']]

    def system_methodHelp(self, name):
        """Returns the documentation for a method"""
        method = self._find_method(self._find_method_name(name))
        if method:
            help = MethodHelp.getdoc(method)
            sig = getattr(method, 'signature', None)
            if sig:
                help += "\n\nMethod signature: %s" % sig
            return help
        return xmlrpclib.Fault(0, "No such method name")
    system_methodHelp.signature = [['string', 'string']]


class MethodHelp(object):
    """Wrapper for formatting doc strings from XMLRPCController
    methods"""
    def __init__(self, doc):
        self.__doc__ = doc

    def getdoc(method):
        """Return a formatted doc string, via inspect.getdoc, from the
        specified XMLRPCController method

        The method's help attribute is used if it exists, otherwise the
        method's doc string is used.
        """
        help = getattr(method, 'help', None)
        if help is None:
            help = method.__doc__
        doc = inspect.getdoc(MethodHelp(help))
        if doc is None:
            return ''
        return doc
    getdoc = staticmethod(getdoc)
