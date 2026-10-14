# encoding: utf-8

'''API functions for searching for and getting data from CKAN.'''
from __future__ import annotations

import uuid
import logging
import json
import socket
from typing import (Container, Optional,
                    Union, Any, cast, Type)

from ckan.common import config, asbool, aslist
import sqlalchemy
from sqlalchemy import text


import ckan
import ckan.lib.dictization
import ckan.logic as logic
import ckan.logic.schema
import ckan.lib.dictization.model_dictize as model_dictize
import ckan.lib.jobs as jobs
import ckan.lib.navl.dictization_functions
import ckan.model as model
import ckan.model.misc as misc
import ckan.plugins as plugins
import ckan.lib.search as search
from ckan.model.follower import ModelFollowingModel
from ckan.lib.search.query import solr_literal

import ckan.lib.plugins as lib_plugins
import ckan.lib.datapreview as datapreview
import ckan.authz as authz

from ckan.common import _
from ckan.types import ActionResult, Context, DataDict, Query, Schema

log = logging.getLogger('ckan.logic')

# Define some shortcuts
# Ensure they are module-private so that they don't get loaded as available
# actions in the action API.
_validate = ckan.lib.navl.dictization_functions.validate
_table_dictize = ckan.lib.dictization.table_dictize
_check_access = logic.check_access
NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
_get_or_bust = logic.get_or_bust

_select = sqlalchemy.sql.select
_or_ = sqlalchemy.or_
_and_ = sqlalchemy.and_
_func = sqlalchemy.func
_case = sqlalchemy.case
_null = sqlalchemy.null














