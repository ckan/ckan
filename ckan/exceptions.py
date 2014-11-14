class CkanException(Exception):
    pass

class EmptyRevisionException(CkanException):
    pass

class CkanUrlException(Exception):
    pass

class CkanVersionException(Exception):
    '''Exception raised by
    :py:func:`~ckan.plugins.toolkit.requires_ckan_version` if the required CKAN
    version is not available.

    '''
    pass
