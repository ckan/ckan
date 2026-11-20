# encoding: utf-8


class CkanException(Exception):
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


class SiteUserNotFound(CkanException):
    """Raised by :py:func:`~ckan.plugins.toolkit.get_site_user` when the site
    user has not been created yet. Run ``ckan db upgrade`` to create it.
    """


class HelperError(Exception):
    """Raised if an attempt to access an undefined helper is made.

    Normally, this would be a subclass of AttributeError, but Jinja2 will
    catch and ignore them. We want this to be an explicit failure re #2908.
    """


class CkanDeprecationWarning(DeprecationWarning):
    pass
