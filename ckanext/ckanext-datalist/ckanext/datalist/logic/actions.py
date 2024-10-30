from .schemas import resources_statistics_combined_schema, users_statistics_combined_schema
from .extended_resource_table import ExtendedResourceTable
from .extended_user_table import ExtendedUserTable
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
        
    if 'start_date' not in data_dict:
        current_date = datetime.now().strftime('%Y-%m-%d')
        data_dict['start_date'] = current_date
    
    if 'end_date' not in data_dict:
        current_date = datetime.now().strftime('%Y-%m-%d')
        data_dict['end_date'] = current_date
        
    if 'organizations' not in data_dict:
        data_dict['organizations'] = [""]
        
    if 'package_name' not in data_dict:
        data_dict['package_name'] = [""]
    
    urls_and_counts = ExtendedResourceTable.get_resources_statistics(data_dict)
    return urls_and_counts

@side_effect_free
def users_statistics(context, data_dict):
    toolkit.check_access("user_check", context, data_dict)

    schema = users_statistics_combined_schema()
    data_dict, errors = toolkit.navl_validate(data_dict, schema)
    
    if errors:
            raise ValidationError(errors)
        
    if 'start_date' not in data_dict:
        current_date = datetime.now().strftime('%Y-%m-%d')
        data_dict['start_date'] = current_date
    
    if 'end_date' not in data_dict:
        current_date = datetime.now().strftime('%Y-%m-%d')
        data_dict['end_date'] = current_date
        
    if 'sys_admin' not in data_dict:
        data_dict['sys_admin'] = [""]
        
    if 'recent_active_days' not in data_dict:
        data_dict['recent_active_days'] = -1
    
    urls_and_counts = ExtendedUserTable.get_users_statistics(data_dict)
    return urls_and_counts