# import datetime
# from sqlalchemy import func
# import ckan.model as model
# import ckan.model.meta as meta

# class ExtendedTrackingSummary(model.TrackingSummary):

#     @classmethod
#     def get_urls_and_counts_all(cls, data_dict):
        
#         query = meta.Session.query(
#             model.tracking_summary_table.c.url,
#             model.tracking_summary_table.c.tracking_date,
#             func.sum(model.tracking_summary_table.c.count).label('total_count') 
#         ). filter(
#             model.tracking_summary_table.c.url.like(f'/dataset/%')
#         )

#         conditions = []
#         conditions.append(model.tracking_summary_table.c.package_id != '~~not~found~~')
        
#         package_ids = '/dataset/'
#         if 'package_name' in data_dict:
#             package_name = data_dict.get('package_name')
            
#             package_id_query = meta.Session.query(
#                 model.tracking_summary_table.c.package_id
#             ).filter(
#                 model.tracking_summary_table.c.url.like(f'/dataset/{package_name}')
#             )
#             package_id_row = package_id_query.first()
#             if package_id_row:
#                 package_ids = package_id_row.package_id
                
#             conditions.append(model.tracking_summary_table.c.url.like(f'/dataset/{package_name}'))
            
#         if conditions:
#             query = query.filter(*conditions)
#             conditions = []
        
#         if 'start_date' in data_dict:
#             start_date = data_dict.get('start_date')
#             start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
#             conditions.append(model.tracking_summary_table.c.tracking_date >= start_date)

#         if 'end_date' in data_dict:
#             end_date = data_dict.get('end_date')
#             end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d') + datetime.timedelta(days=1)
#             conditions.append(model.tracking_summary_table.c.tracking_date < end_date)

#         if conditions:
#             query = query.filter(*conditions)

#         query = query.group_by(
#             model.tracking_summary_table.c.url,
#             model.tracking_summary_table.c.tracking_date,
#         ).order_by(
#             model.tracking_summary_table.c.tracking_date.desc(),
#             func.sum(model.tracking_summary_table.c.count).desc() 
#         )

#         urls_and_counts = [
#             {'dataset': row.url.replace('/dataset/', ''), 'date': row.tracking_date.strftime('%Y-%m-%d'), 'view': row.total_count}
#             for row in query.all()
#         ]
        
#         if data_dict.get('include_resource', False): 
#             resource_query = meta.Session.query(
#                 model.tracking_summary_table.c.url,
#                 model.tracking_summary_table.c.tracking_date,
#                 func.sum(model.tracking_summary_table.c.count).label('total_count')
#             ).filter(
#                 *conditions,
#                 model.tracking_summary_table.c.tracking_type == 'resource',  
#                 model.tracking_summary_table.c.url.like(f'%{package_ids}%')
#             ).group_by(
#                 model.tracking_summary_table.c.url,
#                 model.tracking_summary_table.c.tracking_date,
#             )

#             resource_urls_and_counts = [
#                 {'url-resource': row.url, 'date': row.tracking_date.strftime('%Y-%m-%d'), 'view': row.total_count}
#                 for row in resource_query.all()
#             ]

#             urls_and_counts.extend(resource_urls_and_counts)
        
#         return urls_and_counts


# @classmethod
#     def _get_resources(cls, row, dataset_url):
#         """Helper function to fetch resources including id and name."""
#         package_id_query = meta.Session.query(
#             model.tracking_summary_table.c.package_id
#         ).filter(
#             model.tracking_summary_table.c.url == dataset_url
#         ).first()

#         if not package_id_query:
#             return []

#         # Fetch resource information from the resource table
#         resource_query = meta.Session.query(
#             model.Resource.id,
#             model.Resource.name,
#             model.tracking_summary_table.c.url,
#             func.sum(model.tracking_summary_table.c.count).label('count')
#         ).join(
#             model.Resource, model.tracking_summary_table.c.package_id == model.Resource.package_id
#         ).filter(
#             model.tracking_summary_table.c.url.like(f'%{package_id_query.package_id}%'),
#             model.tracking_summary_table.c.tracking_date == row.tracking_date
#         ).group_by(
#             model.tracking_summary_table.c.url,
#             model.Resource.id,
#             model.Resource.name
#         )

#         resources = [
#             {
#                 'resource': res.url,
#                 'count': res.count,
#                 'resource_id': res.id,
#                 'resource_name': res.name
#             }
#             for res in resource_query.all()
#         ]

#         return resources