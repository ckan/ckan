import warnings

def ErrorMiddleware(*args, **kw):
    warnings.warn(
        'weberror.exceptions.errormiddleware.ErrorMiddleware has been moved '
        'to weberror.errormiddleware.ErrorMiddleware',
        DeprecationWarning, stacklevel=2)
    from weberror.errormiddleware import ErrorMiddleware
    return ErrorMiddleware(*args, **kw)

def handle_exception(*args, **kw):
    warnings.warn(
        'weberror.exceptions.errormiddleware.handle_exception has been moved '
        'to weberror.errormiddleware.handle_exception',
        DeprecationWarning, stacklevel=2)
    from weberror.errormiddleware import handle_exceptions
    return handle_exceptions(*args, **kw)
