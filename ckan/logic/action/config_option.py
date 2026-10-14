
from __future__ import annotations

import logging
import time

import ckan
import ckan.model as model
import ckan.logic.schema as schema_
import ckan.lib.uploader as uploader
import ckan.lib.app_globals as app_globals
from ckan.common import _, config
from ckan.lib import files
from ckan.lib.navl.dictization_functions import validate as _validate
from ckan.logic import (
    ValidationError,
    check_access as _check_access,
    get_or_bust as _get_or_bust,
    side_effect_free,
)
from ckan.types import ActionResult, Context, DataDict

log = logging.getLogger('ckan.logic')


def config_option_update(
        context: Context, data_dict: DataDict) -> ActionResult.ConfigOptionUpdate:
    '''

    .. versionadded:: 2.4

    Allows to modify some CKAN runtime-editable config options

    It takes arbitrary key, value pairs and checks the keys against the
    config options update schema. If some of the provided keys are not present
    in the schema a :py:class:`~ckan.plugins.logic.ValidationError` is raised.
    The values are then validated against the schema, and if validation is
    passed, for each key, value config option:

    * It is stored on the ``system_info`` database table
    * The Pylons ``config`` object is updated.
    * The ``app_globals`` (``g``) object is updated (this only happens for
      options explicitly defined in the ``app_globals`` module.

    The following lists a ``key`` parameter, but this should be replaced by
    whichever config options want to be updated, eg::

        get_action('config_option_update)({}, {
            'ckan.site_title': 'My Open Data site',
        })

    :param key: a configuration option key (eg ``ckan.site_title``). It must
        be present on the ``update_configuration_schema``
    :type key: string

    :returns: a dictionary with the options set
    :rtype: dictionary

    .. note:: You can see all available runtime-editable configuration options
        calling
        the :py:func:`~ckan.logic.action.get.config_option_list` action

    .. note:: Extensions can modify which configuration options are
        runtime-editable.
        For details, check :doc:`/extensions/remote-config-update`.

    .. warning:: You should only add config options that you are comfortable
        they can be edited during runtime, such as ones you've added in your
        own extension, or have reviewed the use of in core CKAN.

    '''
    _check_access('config_option_update', context, data_dict)

    schema = schema_.update_configuration_schema()

    available_options = schema.keys()

    provided_options = data_dict.keys()

    unsupported_options = set(provided_options) - set(available_options)
    if unsupported_options:
        opts = ' '.join(unsupported_options)
        msg = _('Configuration option(s) \'%(opts)s\' can not be updated') % {'opts': opts}

        raise ValidationError({'message': msg})

    upload = uploader.get_uploader('admin')
    upload.update_data_dict(data_dict, 'ckan.site_logo',
                            'logo_upload', 'clear_logo_upload')
    upload.upload(uploader.get_max_image_size())
    data, errors = _validate(data_dict, schema, context)
    if errors:
        model.Session.rollback()
        raise ValidationError(errors)

    for key, value in data.items():

        # Set full Logo url
        if key == 'ckan.site_logo' and value and not value.startswith('http')\
                and not value.startswith('/'):
            try:
                storage = files.get_storage(config["ckan.files.default_storages.admin"])
            except files.exc.UnknownStorageError:
                pass
            else:
                if link := storage.permanent_link(files.FileData(
                    files.Location(value)
                )):
                    value = link

        # Save value in database
        model.set_system_info(key, value)

        # Update CKAN's `config` object
        config[key] = value

        # Only add it to the app_globals (`g`) object if explicitly defined
        # there
        globals_keys = app_globals.app_globals_from_config_details.keys()
        if key in globals_keys:
            app_globals.set_app_global(key, value)

    # Update the config update timestamp
    model.set_system_info('ckan.config_update', str(time.time()))

    log.info('Updated config options: %s', data)

    return data


@side_effect_free
def config_option_show(context: Context,
                       data_dict: DataDict) -> ActionResult.ConfigOptionShow:
    '''Show the current value of a particular configuration option.

    Only returns runtime-editable config options (the ones returned by
    :py:func:`~ckan.logic.action.get.config_option_list`), which can be updated with the
    :py:func:`~ckan.logic.action.update.config_option_update` action.

    :param key: The configuration option key
    :type key: string

    :returns: The value of the config option from either the system_info table or ini file.
    :rtype: string

    :raises: :class:`ckan.logic.ValidationError`: if config option is not in the schema (whitelisted as editable).
    '''

    _check_access('config_option_show', context, data_dict)

    key = _get_or_bust(data_dict, 'key')

    schema = ckan.logic.schema.update_configuration_schema()

    # Only return whitelisted keys
    if key not in schema:
        raise ValidationError({
            'message': f"Configuration option '{key}' can not be shown"})


    # return the value from config
    return config.get(key, None)


@side_effect_free
def config_option_list(context: Context,
                       data_dict: DataDict) -> ActionResult.ConfigOptionList:
    '''Return a list of runtime-editable config options keys that can be
       updated with :py:func:`~ckan.logic.action.update.config_option_update`.

    :returns: A list of config option keys.
    :rtype: list
    '''

    _check_access('config_option_list', context, data_dict)

    schema = ckan.logic.schema.update_configuration_schema()

    return list(schema.keys())
