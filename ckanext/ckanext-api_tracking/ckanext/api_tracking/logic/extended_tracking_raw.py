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
                    'include_resources': cls._get_resources(row) if include_resources else None,    
                    'package_view': row.request_count
                })
        except Exception as e:
            raise ValidationError(f"Error processing results: {e}")

        return list(user_tracking_data.values())

    @classmethod
    def _get_resources(cls, row):
        """Helper function to fetch resources including id and name."""

        try:
            package_id_query = meta.Session.query(
                model.tracking_summary_table.c.package_id
            ).filter(
                model.tracking_summary_table.c.url == row.url
            ).first()

            if not package_id_query:
                return []

            resource_query = meta.Session.query(
                model.tracking_raw_table.c.url,
                func.count(model.tracking_raw_table.c.url).label('count')
            ).filter(
                model.tracking_raw_table.c.url.like(f'%{package_id_query.package_id}%'),
                func.date(model.tracking_raw_table.c.access_timestamp) == row.date,
                model.tracking_raw_table.c.user_key == row.user_key
            ).group_by(
                model.tracking_raw_table.c.url,
            )
            resources = resource_query.all()

        except Exception as e:
            raise ValidationError(f"Error fetching resources: {e}")

        resource_details = []

        for res in resources:
            resource_url = res.url

            resource_id = None
            if '/resource/' in resource_url:
                resource_id = resource_url.split('/resource/')[1].split('/')[0]

            if resource_id:
                try:
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
                            'resource_view': res.count
                        })
                except Exception as e:
                    raise ValidationError(f"Error fetching resource details: {e}")

        return resource_details
    
    @classmethod
    def _get_package_id(cls, row):
        id_query = meta.Session.query(
            model.Package.id,
            ).filter(
            model.Package.name == row.url.replace('/dataset/', '')
            ).first()

        if id_query:
            package_id = id_query.id
        else:
            package_id = None
        
        return package_id
