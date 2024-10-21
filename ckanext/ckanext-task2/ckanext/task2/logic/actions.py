# from .schemas import tracking_by_user_combined_schema
# from .extended_tracking_raw import ExtendedTrackingRaw
# from ckan.plugins.toolkit import side_effect_free, ValidationError
# import ckan.plugins.toolkit as toolkit
# from datetime import datetime

# @side_effect_free
# def tracking_by_user(context, data_dict):
#     toolkit.check_access("tracking_by_user", context, data_dict)

#     schema = tracking_by_user_combined_schema()
#     data_dict, errors = toolkit.navl_validate(data_dict, schema)
    
#     if errors:
#             raise ValidationError(errors)
        
#     if 'start_date' not in data_dict:
#         current_date = datetime.now().strftime('%Y-%m-%d')
#         data_dict['start_date'] = current_date
    
#     if 'end_date' not in data_dict:
#         current_date = datetime.now().strftime('%Y-%m-%d')
#         data_dict['end_date'] = current_date
        
#     if 'user_name' not in data_dict:
#         data_dict['user_name'] = ''
    
#     urls_and_counts = ExtendedTrackingRaw.get_by_user(data_dict)
#     return urls_and_counts
