"""Deprecated: This module has moved to pylons.controllers.util"""
import warnings

import pylons
import pylons.controllers.util
import pylons.legacy
from pylons.util import deprecated, func_move

__all__ = ['abort', 'etag_cache', 'log', 'redirect_to']

warnings.warn('The pylons.helper module has moved to pylons.controllers.util; '
              'please update your imports.', DeprecationWarning, 2)

def log(msg):
    """Deprecated: Use the logging module instead.

    Log a message to the output log.
    """
    warnings.warn(pylons.legacy.log_warning, DeprecationWarning, 2)
    pylons.request.environ['wsgi.errors'].write('=> %s\n' % str(msg))

abort = deprecated(pylons.controllers.util.abort,
                   func_move('abort', 'pylons.controllers.util'))
etag_cache = deprecated(pylons.controllers.util.etag_cache,
                        func_move('etag_cache', 'pylons.controllers.util'))
redirect_to = deprecated(pylons.controllers.util.redirect_to,
                         func_move('redirect_to', 'pylons.controllers.util'))
