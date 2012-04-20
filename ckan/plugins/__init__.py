from ckan.plugins.core import *
from ckan.plugins.interfaces import *


class _Toolkit(object):
    ''' This object allows us to avoid circular imports while making
    functions/objects available to plugins. '''

    def __init__(self):
        self.toolkit = None

    def __getattr__(self, name):
        if not self.toolkit:
            import toolkit
            self.toolkit = toolkit
        return getattr(self.toolkit, name)

toolkit = _Toolkit()
del _Toolkit
