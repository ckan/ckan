from ckan.types import (
    Validator
)
from ckan.logic.schema import validator_args
    
@validator_args    
def tracking_by_user_combined_schema(not_empty: Validator, ignore_missing: Validator, boolean_validator: Validator, 
                                     isodate: Validator, int_validator: Validator):
    return {
        'user_name': [ignore_missing, not_empty],
        'package_name': [ignore_missing, not_empty],
        'start_date': [ignore_missing, not_empty, isodate],
        'end_date': [ignore_missing, not_empty, isodate],
        'include_resources': [ignore_missing, not_empty, boolean_validator],
        'limit': [ignore_missing, not_empty, int_validator],
        'offset': [ignore_missing, not_empty, int_validator],
        'limit_resources': [ignore_missing, not_empty, int_validator],
        'offset_resources': [ignore_missing, not_empty, int_validator],
    }
    
@validator_args    
def tracking_urls_and_counts_combined_schema(not_empty: Validator, ignore_missing: Validator, isodate: Validator, 
                                             boolean_validator: Validator, int_validator: Validator):
    return {
        'package_name': [ignore_missing, not_empty],
        'start_date': [ignore_missing, not_empty, isodate],
        'end_date': [ignore_missing, not_empty, isodate],
        'include_resources': [ignore_missing, not_empty, boolean_validator], 
        'limit': [ignore_missing, not_empty, int_validator],
        'offset': [ignore_missing, not_empty, int_validator]
    }