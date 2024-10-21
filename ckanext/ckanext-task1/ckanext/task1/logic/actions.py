from .schemas import tracking_urls_and_counts_combined_schema
from .extended_tracking_summary import ExtendedTrackingSummary
from .action_result import ActionResult
from ckan.plugins.toolkit import side_effect_free, ValidationError, check_access
import ckan.plugins.toolkit as toolkit
from datetime import datetime

@side_effect_free
def tracking_urls_and_counts(context, data_dict):
    toolkit.check_access("tracking_urls_and_counts1", context, data_dict)

    schema = tracking_urls_and_counts_combined_schema()
    data_dict, errors = toolkit.navl_validate(data_dict, schema)
    
    if errors:
            raise ValidationError(errors)
        
    if 'start_date' not in data_dict:
        current_date = datetime.now().strftime('%Y-%m-%d')
        data_dict['start_date'] = current_date
    
    if 'end_date' not in data_dict:
        current_date = datetime.now().strftime('%Y-%m-%d')
        data_dict['end_date'] = current_date
        
    if 'package_name' not in data_dict:
        data_dict['package_name'] = ''
    
    urls_and_counts = ExtendedTrackingSummary.get_urls_and_counts_all(data_dict)
    return urls_and_counts
