from .schema import tracking_datatypes_get_sum_schema
from ckan.plugins.toolkit import ValidationError
from .tracking_types_resource import TrackingAPI
import ckan.model.meta as meta
import ckan.model as model
from sqlalchemy import func
from ckan.plugins.toolkit import side_effect_free, ValidationError
import ckan.plugins.toolkit as toolkit
from datetime import datetime, timedelta

@side_effect_free
def resource_access_by_date(context, data_dict):
   
    toolkit.check_access("tracking_access", context, data_dict)

    schema = tracking_datatypes_get_sum_schema()
    
    data_dict, errors = toolkit.navl_validate(data_dict, schema)
   
    if errors:
            raise ValidationError(errors)
        
    if 'start_date' not in data_dict:
        current_date = datetime.now()
        data_dict['start_date'] = current_date
    
    if 'end_date' not in data_dict:
        current_date = datetime.now() + timedelta(days=1)
        data_dict['end_date'] = current_date
        
    if 'format_type' not in data_dict:
        data_dict['format_type'] = ''
        
    limit = data_dict.get('limit', 200)  
    offset = data_dict.get('offset', 0) 

    resource_access_by_date = TrackingAPI.get_resource_access_count_by_date(data_dict, limit=limit, offset=offset)
 
    return resource_access_by_date