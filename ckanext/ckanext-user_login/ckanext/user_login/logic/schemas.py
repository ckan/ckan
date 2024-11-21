from ckan.types import (
    Validator
)
from ckan.logic.schema import validator_args
    
@validator_args    
def login_activity_show_schema(not_empty: Validator, ignore_missing: Validator, isodate: Validator,
                                         int_validator: Validator, boolean_validator: Validator):
    return {
        'login_detail': [ignore_missing, not_empty, boolean_validator],
        'user_name': [ignore_missing, not_empty],
        'start_date': [ignore_missing, not_empty, isodate],
        'end_date': [ignore_missing, not_empty, isodate],
        'limit': [ignore_missing, not_empty, int_validator],
        'offset': [ignore_missing, not_empty, int_validator]
    }
   