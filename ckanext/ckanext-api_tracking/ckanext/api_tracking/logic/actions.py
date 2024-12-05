from .schemas import organization_statistics_schema, tracking_by_user_combined_schema, tracking_urls_and_counts_combined_schema, field_statistics_schema
from .extended_tracking_raw import ExtendedTrackingRaw
from .extended_tracking_summary import ExtendedTrackingSummary
from ckan.plugins.toolkit import side_effect_free, ValidationError
import ckan.plugins.toolkit as toolkit
from datetime import datetime
from ..models.statistical_org import OrganizationStatisticsAPI
from ..models.statistiacal_field import FieldStatisticsAPI
import ckan.model.meta as meta
import ckan.model as model

@side_effect_free
def tracking_urls_and_counts(context, data_dict):
    toolkit.check_access("tracking_access", context, data_dict)

    schema = tracking_urls_and_counts_combined_schema()
    data_dict, errors = toolkit.navl_validate(data_dict, schema)
    
    if errors:
            raise ValidationError(errors)
        
    if 'start_date' not in data_dict:
        current_date = datetime.now()
        data_dict['start_date'] = current_date
    
    if 'end_date' not in data_dict:
        current_date = datetime.now()
        data_dict['end_date'] = current_date
        
    if 'package_name' not in data_dict:
        data_dict['package_name'] = [""]
        
    limit = data_dict.get('limit', 200)  
    offset = data_dict.get('offset', 0) 
    
    urls_and_counts = ExtendedTrackingSummary.get_urls_and_counts_all(data_dict, limit=limit, offset=offset)
    return urls_and_counts

@side_effect_free
def tracking_by_user(context, data_dict):
    toolkit.check_access("tracking_access", context, data_dict)

    schema = tracking_by_user_combined_schema()
    data_dict, errors = toolkit.navl_validate(data_dict, schema)
    
    if errors:
            raise ValidationError(errors)
        
    if 'start_date' not in data_dict:
        current_date = datetime.now()
        data_dict['start_date'] = current_date
    
    if 'end_date' not in data_dict:
        current_date = datetime.now()
        data_dict['end_date'] = current_date
        
    if 'user_name' not in data_dict:
        data_dict['user_name'] = [""]
        
    if 'package_name' not in data_dict:
        data_dict['package_name'] = [""]
        
    if 'include_resources' not in data_dict:
        data_dict['include_resources'] = False

    limit = data_dict.get('limit', 200)  
    offset = data_dict.get('offset', 0) 
    
    limit_resources = data_dict.get('limit_resources', 200)  
    offset_resources = data_dict.get('offset_resources', 0)  
    
    urls_and_counts = ExtendedTrackingRaw.get_by_user(data_dict, limit=limit, offset=offset, 
                                                      limit_resources = limit_resources, offset_resources = offset_resources)
    return urls_and_counts

@side_effect_free
def statistical_org_get_sum(context, data_dict):
    toolkit.check_access("tracking_access", context, data_dict)

    schema = organization_statistics_schema()
    
    data_dict, errors = toolkit.navl_validate(data_dict, schema)

    if errors:
        raise toolkit.ValidationError(errors)


    if 'organization_name' not in data_dict or data_dict['organization_name'] == '':
        # Lấy tên tổ chức đầu tiên từ cơ sở dữ liệu
        first_org_query = meta.Session.query(model.Group.name).filter(model.Group.is_organization == True).first()
        if first_org_query:
            data_dict['organization_name'] = first_org_query[0]  # Gán giá trị tổ chức đầu tiên vào data_dict
    
    if 'private' not in data_dict:
        data_dict['private'] = None  # Nếu không có giá trị mặc định là None (cả true, false)
        
    if 'state' not in data_dict:
        data_dict['state'] = ""  # Nếu không có trạng thái, mặc định là None
    
    if 'include_datasets' not in data_dict:
        data_dict['include_datasets'] = False
    
    statistical_org = OrganizationStatisticsAPI.get_organization_package_status(data_dict)
    return statistical_org

@side_effect_free
def statistical_field_get_sum(context, data_dict):
    toolkit.check_access("tracking_access", context, data_dict)

    schema = field_statistics_schema()
    
    data_dict, errors = toolkit.navl_validate(data_dict, schema)

    if errors:
        raise toolkit.ValidationError(errors)

    if 'field_name' not in data_dict:
        data_dict['field_name'] = [""]
   
    if 'private' not in data_dict:
        data_dict['private'] = None  # Nếu không có giá trị mặc định là None (cả true, false)
        
    if 'state' not in data_dict:
        data_dict['state'] = ""  # Nếu không có trạng thái, mặc định là None
    
    if 'include_datasets' not in data_dict:
        data_dict['include_datasets'] = False
    
    statistical_org = FieldStatisticsAPI.get_field_package_status(data_dict)
    return statistical_org


