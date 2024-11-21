from .schemas import resources_statistics_combined_schema, users_statistics_combined_schema, new_users_statistics_combined_schema
from ..model.extended_resource_table import ExtendedResourceTable
from ..model.extended_user_table import ExtendedUserTable
from ckan.plugins.toolkit import side_effect_free, ValidationError
import ckan.plugins.toolkit as toolkit
from datetime import datetime

@side_effect_free
def resources_statistics(context, data_dict):
    toolkit.check_access("user_check", context, data_dict)

    schema = resources_statistics_combined_schema()
    data_dict, errors = toolkit.navl_validate(data_dict, schema)
    
    if errors:
            raise ValidationError(errors)
        
    limit = data_dict.get('limit', 10)  
    offset = data_dict.get('offset', 0) 
    
    result = ExtendedResourceTable.get_resources_statistics(data_dict, limit=limit, offset=offset)
    return result

@side_effect_free
def users_statistics(context, data_dict):
    toolkit.check_access("user_check", context, data_dict)

    schema = users_statistics_combined_schema()
    data_dict, errors = toolkit.navl_validate(data_dict, schema)
    
    if errors:
            raise ValidationError(errors)
        
    if 'recent_active_days' not in data_dict:
        data_dict['recent_active_days'] = 1
            
    result = ExtendedUserTable.get_users_statistics(data_dict)
    return result

@side_effect_free
def new_users_statistics(context, data_dict):
    toolkit.check_access("user_check", context, data_dict)

    schema = new_users_statistics_combined_schema()
    data_dict, errors = toolkit.navl_validate(data_dict, schema)
    
    if errors:
            raise ValidationError(errors)
        
    result = ExtendedUserTable.get_new_users_statistics(data_dict)
    return result