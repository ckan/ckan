from __future__ import annotations

import ckan
import ckan.authz as authz
import ckan.logic as logic
from ckan.common import config
from ckan.logic import (
    NotFound,
    check_access as _check_access,
    side_effect_free,
)
from ckan.types import ActionResult, Context, DataDict


@side_effect_free
def status_show(context: Context, data_dict: DataDict) -> ActionResult.StatusShow:
    '''Return a dictionary with information about the site's configuration.

    :rtype: dictionary

    '''
    _check_access('status_show', context, data_dict)
    extensions = config.get('ckan.plugins')

    site_info = {
        'site_title': config.get('ckan.site_title'),
        'site_description': config.get('ckan.site_description'),
        'site_url': config.get('ckan.site_url'),
        'error_emails_to': config.get('email_to'),
        'locale_default': config.get('ckan.locale_default'),
        'extensions': extensions,
    }
    if not config.get('ckan.hide_version') or authz.is_sysadmin(context['user']):
        site_info['ckan_version'] = ckan.__version__
    return site_info


@side_effect_free
def help_show(context: Context, data_dict: DataDict) -> ActionResult.HelpShow:
    '''Return the help string for a particular API action.

    :param name: Action function name (eg `user_create`, `package_search`)
    :type name: string
    :returns: The help string for the action function, or None if the function
              does not have a docstring.
    :rtype: string

    :raises: :class:`ckan.logic.NotFound`: if the action function doesn't exist

    '''

    function_name = logic.get_or_bust(data_dict, 'name')

    _check_access('help_show', context, data_dict)

    try:
        function = logic.get_action(function_name)
    except KeyError:
        raise NotFound('Action function not found')

    return function.__doc__