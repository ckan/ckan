# import datetime
# from sqlalchemy import func
# import ckan.model as model
# import ckan.model.meta as meta
# from ckan.plugins.toolkit import ValidationError

# class ExtendedTrackingRaw(model.TrackingSummary):

#     @classmethod
#     def get_by_user(cls, data_dict):
        
#         start_date = datetime.datetime.strptime(data_dict.get('start_date'), '%Y-%m-%d')
#         end_date = datetime.datetime.strptime(data_dict.get('end_date'), '%Y-%m-%d') + datetime.timedelta(days=1)
#         user_name = data_dict['user_name']
        
#         try:
#             query = meta.Session.query(
#                 model.user_table.c.name,
#                 model.tracking_raw_table.c.url,
#                 func.date(model.tracking_raw_table.c.access_timestamp).label('date'),
#                 func.count(model.tracking_raw_table.c.user_key).label('request_count')
#             ).join(
#                 model.user_table,  
#                 model.tracking_raw_table.c.user_key == model.user_table.c.id  
#             ).filter(
#                 model.tracking_raw_table.c.url.like(f'/dataset/%'),
#                 func.date(model.tracking_raw_table.c.access_timestamp) >= start_date,
#                 func.date(model.tracking_raw_table.c.access_timestamp) < end_date,
#                 model.user_table.c.name == user_name
#             ).group_by(
#                 model.user_table.c.name,  
#                 model.tracking_raw_table.c.url,
#                 func.date(model.tracking_raw_table.c.access_timestamp)
#             ).order_by(
#                 func.date(model.tracking_raw_table.c.access_timestamp).desc()
#             )
#         except Exception as e:
#             raise ValidationError(f"Database query error: {e}")
            
#         results = query.all()

#         try:
#             urls_and_counts = [
#                 {
#                     'user_key': row.name,  
#                     'date': row.date, 
#                     'page': (
#                         cls._get_dataset_by_resource(row.url) if '/resource/' in row.url
#                         else row.url.replace('/', '') if '/dataset/' == row.url
#                         else row.url.replace('/dataset/', '') if '/dataset/' in row.url
#                         else row.url  
#                     ),
#                     'resource_name': cls._get_resource(row.url) if '/resource/' in row.url else None,
#                     'count': row.request_count, 
#                 }
#                 for row in results
#             ]
#         except Exception as e:
#             raise ValidationError(f"Error processing results: {e}")

#         return urls_and_counts

#     @classmethod
#     def _get_resource(cls, url):
#         try:
#             resource_id = url.split('/resource/')[1].split('/')[0]
        
#             resource_info = meta.Session.query(
#                 model.Resource.name
#             ).filter(
#                 model.Resource.id == resource_id
#             ).first()
        
#             if resource_info is None:
#                 raise ValidationError(f"Resource with id {resource_id} not found.")
        
#         except IndexError:
#             raise ValidationError(f"Invalid URL format: {url}")
#         except Exception as e:
#             raise ValidationError(f"Error fetching resource details: {e}")
    
#         return resource_info.name
    
#     @classmethod
#     def _get_dataset_by_resource(cls, url):
#         try:
#             package_id = url.split('/dataset/')[1].split('/')[0] 

#             query = meta.Session.query(
#                 model.tracking_summary_table.c.url,
#             ).filter(
#                 model.tracking_summary_table.c.package_id == package_id
#             ).first()
        
#             result = query.url.replace('/dataset/', '')
#             return result if query else []  
#         except Exception as e:
#             raise ValidationError(f"Error fetching dataset by resource: {e}")