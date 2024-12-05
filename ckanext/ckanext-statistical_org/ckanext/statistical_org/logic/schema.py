from ckan.types import (
    Validator
)
from ckan.logic.schema import validator_args

@validator_args    
def organization_statistics_schema(not_empty: Validator, ignore_missing: Validator, boolean_validator: Validator):
    return {
        'id_org': [ignore_missing, not_empty],
        'private': [ignore_missing, not_empty,boolean_validator],
        'state': [ignore_missing, not_empty],
        'include_datasets': [ignore_missing, not_empty, boolean_validator],
    }
