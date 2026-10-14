# encoding: utf-8

'''API functions for partial updates of existing data in CKAN'''

from ckan import model
from ckan.logic import (
    get_action as _get_action,
    check_access as _check_access,
    get_or_bust as _get_or_bust,
    fresh_context as _fresh_context,
    NotFound,
)
from ckan.types import Context, DataDict
from ckan.types.logic import ActionResult












