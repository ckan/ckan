import datetime
from sqlalchemy import func
import ckan.model as model
import ckan.model.meta as meta
from ckan.plugins.toolkit import ValidationError

class ExtendedTrackingSummary(model.TrackingSummary):

    @classmethod
    def get_urls_and_counts_all(cls, data_dict):
        
        start_date = datetime.datetime.strptime(data_dict.get('start_date'), '%Y-%m-%d')
        end_date = datetime.datetime.strptime(data_dict.get('end_date'), '%Y-%m-%d') + datetime.timedelta(days=1)
        package_name = data_dict['package_name']
        
        try:
            query = meta.Session.query(
                model.tracking_summary_table.c.url,
                model.tracking_summary_table.c.tracking_date,
                model.tracking_summary_table.c.package_id,
                func.sum(model.tracking_summary_table.c.count).label('total_count')
            ).filter(
                model.tracking_summary_table.c.url.like(f'/dataset/%'),
                model.tracking_summary_table.c.package_id != '~~not~found~~',
                model.tracking_summary_table.c.tracking_date >= start_date,
                model.tracking_summary_table.c.tracking_date < end_date,
                model.tracking_summary_table.c.url.like(f'%/dataset/{package_name}%')
            ).group_by(
                model.tracking_summary_table.c.url,
                model.tracking_summary_table.c.tracking_date,
                model.tracking_summary_table.c.package_id
            ).order_by(
                model.tracking_summary_table.c.tracking_date.desc(),
                func.sum(model.tracking_summary_table.c.count).desc()
            )
        except Exception as e:
            raise ValidationError(f"Database query error: {e}")

        results = query.all()
        include_resource = data_dict.get('include_resource', False)

        try:
            urls_and_counts = [
                {
                    'dataset': row.url.replace('/dataset/', ''),
                    'date': row.tracking_date.strftime('%Y-%m-%d'),
                    'view': row.total_count,
                    'include_resources': cls._get_resources(row) if include_resource else []
                }
                for row in results
            ]
        except Exception as e:
            raise ValidationError(f"Error processing results: {e}")

        return urls_and_counts

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
                model.tracking_summary_table.c.url,
                func.sum(model.tracking_summary_table.c.count).label('count')
            ).filter(
                model.tracking_summary_table.c.url.like(f'%{package_id_query.package_id}%'),
                model.tracking_summary_table.c.tracking_date == row.tracking_date
            ).group_by(
                model.tracking_summary_table.c.url,
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
                            'resource_id': resource_info.id,
                            'resource_name': resource_info.name,
                            'view': res.count
                        })
                except Exception as e:
                    raise ValidationError(f"Error fetching resource details: {e}")

        return resource_details