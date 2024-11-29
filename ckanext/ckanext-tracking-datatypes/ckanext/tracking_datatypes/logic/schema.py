from ckan.types import (
    Validator
)
from ckan.logic.schema import validator_args

@validator_args    
def tracking_datatypes_get_sum_schema(not_empty: Validator, ignore_missing: Validator,
                                     isodate: Validator, int_validator: Validator):
    return {
        'start_date': [ignore_missing, not_empty, isodate],
        'end_date': [ignore_missing, not_empty, isodate],
        'format_type': [ignore_missing, not_empty],
        'limit': [ignore_missing, not_empty, int_validator],
        'offset': [ignore_missing, not_empty, int_validator]
    }
