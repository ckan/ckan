import ckan.plugins.toolkit as tk
from .schema import organization_statistics_schema
from .statistical_org import OrganizationStatisticsAPI

@tk.side_effect_free
def statistical_org_get_sum(context, data_dict):
    tk.check_access("check_auth_statistical", context, data_dict)

    schema = organization_statistics_schema()
    print("+==========schema", schema)
    
    data_dict, errors = tk.navl_validate(data_dict, schema)

    if errors:
        raise tk.ValidationError(errors)


    if 'private' not in data_dict:
        data_dict['private'] = None  # Nếu không có giá trị mặc định là None (cả true, false)
        
    if 'state' not in data_dict:
        data_dict['state'] = None  # Nếu không có trạng thái, mặc định là None
    
    if 'include_datasets' not in data_dict:
        data_dict['include_datasets'] = False
    
    statistical_org = OrganizationStatisticsAPI.get_organization_package_status(data_dict)
    return statistical_org