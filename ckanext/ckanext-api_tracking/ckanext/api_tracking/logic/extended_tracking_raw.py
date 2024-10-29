import datetime
from sqlalchemy import func
import ckan.model as model
import ckan.model.meta as meta
from ckan.plugins.toolkit import ValidationError

class ExtendedTrackingRaw(model.TrackingSummary):

    @classmethod
    def get_by_user(cls, data_dict):
        
        start_date = datetime.datetime.strptime(data_dict.get('start_date'), '%Y-%m-%d')
        end_date = datetime.datetime.strptime(data_dict.get('end_date'), '%Y-%m-%d') + datetime.timedelta(days=1)
        user_names = data_dict['user_name']
        package_name = data_dict['package_name']
        include_resources = data_dict.get('include_resources')
        
        try:
            query = meta.Session.query(
                model.user_table.c.name,
                model.tracking_raw_table.c.url,
                model.tracking_raw_table.c.tracking_type,
                model.tracking_raw_table.c.user_key,
                func.date(model.tracking_raw_table.c.access_timestamp).label('date'),
                func.count(model.tracking_raw_table.c.user_key).label('request_count')
            ).join(
                model.user_table,  
                model.tracking_raw_table.c.user_key == model.user_table.c.id  
            ).filter(
                model.tracking_raw_table.c.url.like(f'/dataset/%'),
                model.tracking_raw_table.c.tracking_type == 'page',
                func.date(model.tracking_raw_table.c.access_timestamp) >= start_date,
                func.date(model.tracking_raw_table.c.access_timestamp) < end_date,
                model.user_table.c.name.in_(user_names) if data_dict['user_name'] != [""] else True,
                func.replace(model.tracking_raw_table.c.url, '/dataset/', '').in_(package_name) if data_dict['package_name'] != [""] else True
            ).group_by(
                model.user_table.c.name,  
                model.tracking_raw_table.c.url,
                model.tracking_raw_table.c.tracking_type,
                model.tracking_raw_table.c.user_key,
                func.date(model.tracking_raw_table.c.access_timestamp),
            ).order_by(
                func.date(model.tracking_raw_table.c.access_timestamp).desc()
            )
        except Exception as e:
            raise ValidationError(f"Database query error: {e}")
            
        results = query.all()

        user_tracking_data = {}

        try:
            for row in results:
                user_key = row.name
                
                if user_key not in user_tracking_data:
                    user_tracking_data[user_key] = {
                        'user_name': user_key,
                        'tracking': []
                    }

                user_tracking_data[user_key]['tracking'].append({
                    'date': row.date, 
                    'package': row.url.replace('/dataset/', ''),
                    'package_id': cls._get_package_id(row),
                    'include_resource': cls._fetch_resources(row) if include_resources else None,
                    'package_view': row.request_count
                })
        except Exception as e:
            raise ValidationError(f"Error processing results: {e}")

        return list(user_tracking_data.values())
    
    @classmethod
    def _get_package_id(cls, row):
        id_query = meta.Session.query(model.Package.id).filter(
            model.Package.name == row.url.replace('/dataset/', '')
        ).first()
        return id_query.id if id_query else None

    @classmethod
    def _fetch_resources(cls, row): 
        """Helper function to fetch resources including id and name."""

        resource_details = []

        try:
            package_id_query = meta.Session.query(
                model.tracking_summary_table.c.package_id
            ).filter(
                model.tracking_summary_table.c.url == row.url
            ).first()

            if not package_id_query:
                return []
            
            resources_id_query = meta.Session.query(
                model.Resource.id
            ).filter(
                model.Resource.package_id == package_id_query.package_id
            )
            
            for res in resources_id_query:
                resource_id = res.id
                
                resource_query = meta.Session.query(
                    model.tracking_raw_table.c.url,
                ).filter(
                    model.tracking_raw_table.c.url.like(f'%/{res.id}%'), 
                    func.date(model.tracking_raw_table.c.access_timestamp) == row.date,
                    model.tracking_raw_table.c.user_key == row.user_key,
                    model.tracking_raw_table.c.tracking_type.in_(['download', 'resource'])            
                ).group_by(
                    model.tracking_raw_table.c.url,
                ).first()
                
                if resource_query:
                    resource_info = meta.Session.query(
                        model.Resource.id,
                        model.Resource.name
                    ).filter(
                        model.Resource.id == resource_id
                    ).first()
                    
                    if resource_info:
                        resource_details.append({
                            'resource_name': resource_info.name,
                            'resource_id': resource_info.id,
                            'download_count': cls._get_view_count(resource_id, row, "download"),
                            'resource_view': cls._get_view_count(resource_id, row, "resource")
                        })

        except Exception as e:
            raise ValidationError(f"Error fetching resources: {e}")   

        return resource_details

    @classmethod
    def _get_view_count(cls, resource_id, row, tracking_type):
        try:
            resource_query = meta.Session.query(
                func.count(model.tracking_raw_table.c.url).label('count')
            ).filter(
                model.tracking_raw_table.c.url.like(f'%{resource_id}%'),
                func.date(model.tracking_raw_table.c.access_timestamp) == row.date,
                model.tracking_raw_table.c.user_key == row.user_key,
                model.tracking_raw_table.c.tracking_type == tracking_type
            ).first()
            return resource_query.count if resource_query else 0

        except Exception as e:
            raise ValidationError(f"Error fetching {tracking_type} view count: {e}")
