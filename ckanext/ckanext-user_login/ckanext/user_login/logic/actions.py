from .schemas import login_activity_show_schema
from ckan.plugins.toolkit import side_effect_free, ValidationError
import ckan.plugins.toolkit as toolkit
from ..model.extendedActivityTable import ExtendedActivityTable
from datetime import datetime

@side_effect_free
def login_activity_show(context, data_dict):
    toolkit.check_access("login_activity_show", context, data_dict)

    schema = login_activity_show_schema()
    data_dict, errors = toolkit.navl_validate(data_dict, schema)
    
    if errors:
            raise ValidationError(errors)
    
    urls_and_counts = ExtendedActivityTable.get_login_activity_stats(data_dict)
    return urls_and_counts