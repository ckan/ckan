from ckan.types import (
    Validator
)
from ckan.logic.schema import validator_args
from .validators import max_30_days_validator
    
@validator_args    
def resources_statistics_combined_schema(not_empty: Validator, ignore_missing: Validator, isodate: Validator,
                                         int_validator: Validator):
    return {
        'organizations': [ignore_missing, not_empty],
        'package_name': [ignore_missing, not_empty],
        'start_date': [ignore_missing, not_empty, isodate],
        'end_date': [ignore_missing, not_empty, isodate],
        'limit': [ignore_missing, not_empty, int_validator],
        'offset': [ignore_missing, not_empty, int_validator]
    }
 
@validator_args    
def users_statistics_combined_schema(not_empty: Validator, ignore_missing: Validator, 
                                     boolean_validator: Validator, isodate: Validator,
                                     int_validator: Validator):
    return {
        'sys_admin': [ignore_missing, not_empty, boolean_validator],
        'recent_active_days': [ignore_missing, not_empty, int_validator, max_30_days_validator],
        'start_created_date': [ignore_missing, not_empty, isodate],
        'end_created_date': [ignore_missing, not_empty, isodate],
        'target_active_date': [ignore_missing, not_empty, isodate],
        'include_user_info_detail': [ignore_missing, not_empty, boolean_validator]
    }