import inspect
from functools import wraps
from ckan.types import (
    Validator
)
from ckan.logic.schema import validator_args

from .validators import validate_date
    
@validator_args    
def tracking_urls_and_counts_combined_schema(not_empty: Validator, ignore_missing: Validator):
    return {
        'package_name': [ignore_missing, not_empty],
        'start_date': [ignore_missing, not_empty, validate_date],
        'end_date': [ignore_missing, not_empty, validate_date],
        'include_resource': [ignore_missing, not_empty]
    }