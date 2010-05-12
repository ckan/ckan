'''For unit testing that does not use paste fixture web requests, but needs
pylons set up for access to c, g or the template engine.

Based on answer at:
http://groups.google.com/group/pylons-discuss/browse_thread/thread/5f8d8f59fd459a77
'''

from unittest import TestCase 
from paste.registry import Registry 
import pylons 
from pylons.util import ContextObj 
from pylons.controllers.util import Request, Response 

from ckan.tests import *

class MockTranslator(object): 
    def ugettext(self, value): 
        return value 

class PylonsTestCase(TestController): 
    """A basic test case which allows access to pylons.c and pylons.request. 
    """ 
    def setUp(self): 
        self.registry=Registry() 
        self.registry.prepare() 

        self.context_obj=ContextObj() 
        self.registry.register(pylons.c, self.context_obj)
        pylons.c.errors = None

        self.request_obj=Request(dict(HTTP_HOST="nohost")) 
        self.registry.register(pylons.request, self.request_obj) 

        self.translator_obj=MockTranslator() 
        self.registry.register(pylons.translator, self.translator_obj) 

        self.buffet = pylons.templating.Buffet('genshi', template_root='ckan.templates')
        self.registry.register(pylons.buffet, self.buffet)

        self.registry.register(pylons.response, Response())
        self.registry.register(pylons.url, None)
