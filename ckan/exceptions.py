# encoding: utf-8


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


class CkanConfigurationException(Exception):
    pass


class HelperError(Exception):
    """Raised if an attempt to access an undefined helper is made.

    Normally, this would be a subclass of AttributeError, but Jinja2 will
    catch and ignore them. We want this to be an explicit failure re #2908.
    """
