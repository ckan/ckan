# encoding: utf-8
"""This module is intended to make functions/objects consistently available to
plugins, whilst giving core CKAN developers the ability move code around or
change underlying frameworks etc.

It should not be used internally within ckan - only by extensions.

Functions/objects should only be removed after reasonable deprecation notice
has been given.

"""
from __future__ import annotations

from typing import Any, Optional, Union
import ckan
import ckan.lib.base as base
from ckan.lib.base import render, abort

from ckan.logic import (  # noqa: re-export
    get_action,
    check_access,
    get_validator,
    chained_auth_function,
    chained_action,
    NotFound as ObjectNotFound,
    NotAuthorized,
    ValidationError,
    UnknownValidator,
    get_or_bust,
    side_effect_free,
    auth_sysadmins_check,
    auth_allow_anonymous_access,
    auth_disallow_anonymous_access,
    fresh_context,
)

import ckan.plugins.blanket as blanket
import ckan.lib.signals as signals
from ckan.lib.jobs import enqueue as enqueue_job
from ckan.logic.validators import Invalid
from ckan.lib.navl.dictization_functions import (
    validate as navl_validate,
    missing,
    StopOnError,
)
from ckan.lib.helpers import (
    helper_functions as h,
    literal,
    chained_helper,
    redirect_to,
    url_for
)
from ckan.exceptions import (
    CkanVersionException,
    HelperError,
)
from ckan.common import (
    CKANConfig,
    config,
    _,
    ungettext,
    c,
    g,
    request,
    asbool,
    asint,
    aslist,
    login_user,
    logout_user,
    current_user
)

from ckan.lib.plugins import (
    DefaultDatasetForm,
    DefaultGroupForm,
    DefaultOrganizationForm,
)
from ckan.cli import error_shout

from ckan.lib.mailer import mail_recipient, mail_user
from ckan.model.base import BaseModel

__all__ = [
    "ckan", "base", "render", "abort",
    "get_action", "check_access",
    "get_validator", "get_converter",
    "chained_auth_function", "chained_action",
    "ObjectNotFound", "NotAuthorized", "ValidationError", "UnknownValidator",
    "get_or_bust",
    "side_effect_free", "auth_sysadmins_check",
    "auth_allow_anonymous_access", "auth_disallow_anonymous_access",
    "blanket", "signals", "enqueue_job",
    "Invalid", "navl_validate", "missing", "StopOnError",
    "h", "literal", "chained_helper", "redirect_to", "url_for",
    "CkanVersionException", "HelperError",
    "config", "_", "ungettext", "g", "c", "request",
    "asbool", "asint", "aslist", "login_user", "logout_user", "current_user",
    "DefaultDatasetForm", "DefaultGroupForm", "DefaultOrganizationForm",
    "error_shout",
    "mail_recipient", "mail_user",
    "render_snippet", "add_template_directory", "add_public_directory",
    "add_resource", "add_ckan_admin_tab",
    "check_ckan_version", "requires_ckan_version", "get_endpoint",
    "fresh_context", "BaseModel",
]

get_converter = get_validator


# Wrapper for the render_snippet function as it uses keywords rather than
# dict to pass data.
def render_snippet(template: str, data: Optional[dict[str, Any]] = None):
    """Render a template snippet and return the output.

    See :doc:`/theming/index`.

    """
    data = data or {}
    return base.render_snippet(template, **data)


def add_template_directory(config_: CKANConfig, relative_path: str):
    """Add a path to the :ref:`extra_template_paths` config setting.

    The path is relative to the file calling this function.

    """
    _add_served_directory(config_, relative_path, "plugin_template_paths")


def add_public_directory(config_: CKANConfig, relative_path: str):
    """Add a path to the :ref:`extra_public_paths` config setting.

    The path is relative to the file calling this function.

    Webassets addition: append directory to webassets load paths
    in order to correctly rewrite relative css paths and resolve
    public urls.

    """
    from ckan.lib.helpers import _local_url
    from ckan.lib.webassets_tools import add_public_path

    path = _add_served_directory(config_, relative_path, "plugin_public_paths")
    url = _local_url("/", locale="default")
    add_public_path(path, url)


def _add_served_directory(
        config_: CKANConfig, relative_path: str, config_var: str):
    """Add extra public/template directories to config."""
    import inspect
    import os

    assert config_var in ("plugin_template_paths", "plugin_public_paths")
    # we want the filename that of the function caller but they will
    # have used one of the available helper functions
    filename = inspect.stack()[2].filename

    this_dir = os.path.dirname(filename)
    absolute_path = os.path.join(this_dir, relative_path)
    if absolute_path not in config_.get(config_var, []):
        if config_var in config_:
            config_[config_var] = [absolute_path] + config_[config_var]
        else:
            config_[config_var] = [absolute_path]
    return absolute_path


def add_resource(path: str, name: str):
    """Add a WebAssets library to CKAN.

    WebAssets libraries are directories containing static resource
    files (e.g. CSS, JavaScript or image files) that can be
    compiled into WebAsset Bundles.

    See :doc:`/theming/index` for more details.

    """
    import inspect
    import os
    from ckan.lib.webassets_tools import create_library

    # we want the filename that of the function caller but they
    # will have used one of the available helper functions
    filename = inspect.stack()[1].filename

    this_dir = os.path.dirname(filename)
    absolute_path = os.path.join(this_dir, path)
    create_library(name, absolute_path)


def add_ckan_admin_tab(
        config_: CKANConfig, route_name: str, tab_label: str,
        config_var: str = "ckan.admin_tabs", icon: Optional[str] = None
):
    """
    Update 'ckan.admin_tabs' dict the passed config dict.
    """
    # get the admin_tabs dict from the config, or an empty dict.
    admin_tabs_dict = config_.get(config_var)
    # update the admin_tabs dict with the new values
    admin_tabs_dict.update({route_name: {"label": tab_label, "icon": icon}})
    # update the config with the updated admin_tabs dict
    config_.update({config_var: admin_tabs_dict})


def _version_str_2_list(v_str: str):
    """convert a version string into a list of ints
    eg 1.6.1b --> [1, 6, 1]"""
    import re

    v_str = re.sub(r"[^0-9.]", "", v_str)
    return [int(part) for part in v_str.split(".")]


def check_ckan_version(
        min_version: Optional[str] = None, max_version: Optional[str] = None):
    """Return ``True`` if the CKAN version is greater than or equal to
    ``min_version`` and less than or equal to ``max_version``,
    return ``False`` otherwise.

    If no ``min_version`` is given, just check whether the CKAN version is
    less than or equal to ``max_version``.

    If no ``max_version`` is given, just check whether the CKAN version is
    greater than or equal to ``min_version``.

    :param min_version: the minimum acceptable CKAN version,
        eg. ``'2.1'``
    :type min_version: string

    :param max_version: the maximum acceptable CKAN version,
        eg. ``'2.3'``
    :type max_version: string

    """
    current = _version_str_2_list(ckan.__version__)

    if min_version:
        min_required = _version_str_2_list(min_version)
        if current < min_required:
            return False
    if max_version:
        max_required = _version_str_2_list(max_version)
        if current > max_required:
            return False
    return True


def requires_ckan_version(min_version: str, max_version: Optional[str] = None):
    """Raise :py:exc:`~ckan.plugins.toolkit.CkanVersionException` if the
    CKAN version is not greater than or equal to ``min_version`` and
    less then or equal to ``max_version``.

    If no ``max_version`` is given, just check whether the CKAN version is
    greater than or equal to ``min_version``.

    Plugins can call this function if they require a certain CKAN version,
    other versions of CKAN will crash if a user tries to use the plugin
    with them.

    :param min_version: the minimum acceptable CKAN version,
        eg. ``'2.1'``
    :type min_version: string

    :param max_version: the maximum acceptable CKAN version,
        eg. ``'2.3'``
    :type max_version: string

    """
    if not check_ckan_version(
        min_version=min_version, max_version=max_version
    ):
        if not max_version:
            error = "Requires ckan version %s or higher" % min_version
        else:
            error = "Requires ckan version between {0} and {1}".format(
                min_version, max_version
            )
        raise CkanVersionException(error)


def get_endpoint() -> Union[tuple[str, str], tuple[None, None]]:
    """Returns tuple in format: (blueprint, view)."""
    # skip CLI requests and requests with unallowed method
    if not request or not request.endpoint:
        return None, None

    blueprint, *rest = request.endpoint.split(".", 1)
    # service routes, like `static`
    view = rest[0] if rest else "index"
    return blueprint, view


# For some members in the the toolkit (e.g. that are exported from
# third-party libraries) we override their docstrings by putting our
# own docstrings into this dict. The Sphinx plugin that documents this
# plugins toolkit will use these docstring overrides instead of the
# object's actual docstring, when present.
docstring_overrides = {
    "config": """The CKAN configuration object.

It stores the configuration values defined in the :ref:`config_file`, eg::

    title = toolkit.config.get("ckan.site_title")

""",
    "_": """Translates a string to the current locale.

The ``_()`` function is a reference to the ``ugettext()`` function.
Everywhere in your code where you want strings to be internationalized
(made available for translation into different languages), wrap them in the
``_()`` function, eg.::

    msg = toolkit._("Hello")

Returns the localized unicode string.
""",
    "ungettext": """Translates a string with
plural forms to the current locale.

Mark a string for translation that has pural forms in the format
``ungettext(singular, plural, n)``. Returns the localized unicode string of
the pluralized value.

Mark a string to be localized as follows::

    msg = toolkit.ungettext("Mouse", "Mice", len(mouses))

""",
    "c": """The Pylons template context object.

[Deprecated]: Use ``toolkit.g`` instead.

This object is used to pass request-specific information to different parts of
the code in a thread-safe way (so that variables from different requests being
executed at the same time don't get confused with each other).

Any attributes assigned to :py:attr:`~ckan.plugins.toolkit.c` are
available throughout the template and application code, and are local to the
current request.

""",
    "g": """The Flask global object.

This object is used to pass request-specific information to different parts of
the code in a thread-safe way (so that variables from different requests being
executed at the same time don't get confused with each other).

Any attributes assigned to :py:attr:`~ckan.plugins.toolkit.g` are
available throughout the template and application code, and are local to the
current request.

It is a bad pattern to pass variables to the templates using the ``g`` object.
Pass them explicitly from the view functions as ``extra_vars``, eg::

    return toolkit.render(
        'myext/package/read.html',
        extra_vars={
            u'some_var': some_value,
            u'some_other_var': some_other_value,
        }
    )

""",
    "request": """Flask request object.

A new request object is created for each HTTP request. It has methods and
attributes for getting things like the request headers, query-string variables,
request body variables, cookies, the request URL, etc.

""",
    "ckan": "``ckan`` package itself.",
    "BaseModel": """Base class for SQLAlchemy declarative models.

Models extending ``BaseModel`` class are attached to the SQLAlchemy's metadata
object automatically::

    from ckan.plugins import toolkit

    class ExtModel(toolkit.BaseModel):
        __tablename__ = "ext_model"
        id = Column(String(50), primary_key=True)
        ...

""",

}
