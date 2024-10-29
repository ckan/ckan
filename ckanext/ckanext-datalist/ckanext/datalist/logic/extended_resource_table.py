import datetime
from sqlalchemy import func, literal
import ckan.model as model
import ckan.model.meta as meta
from ckan.plugins.toolkit import ValidationError

class ExtendedResourceTable(model.Resource):

    @classmethod
    def get_resources_statistics(cls, data_dict):
        
        start_date = datetime.datetime.strptime(data_dict.get('start_date'), '%Y-%m-%d')
        end_date = datetime.datetime.strptime(data_dict.get('end_date'), '%Y-%m-%d') + datetime.timedelta(days=1)
        organizations = data_dict['organizations']
        package_name = data_dict['package_name']
        
        try:
            query = meta.Session.query(
                model.Resource.name.label('resource_name'), 
                model.Resource.id.label('resource_id'),
                model.Resource.format,
                func.date(model.Resource.created).label('created_date'),
                model.Package.name.label('package_name'),
                model.Group.name.label('organization'),
                (literal('/dataset/') + model.Package.id + 
                 literal('/resource/') + model.Resource.id + 
                 literal('/download/') + model.Resource.url).label('download_url'),
            ).join(
                model.Package,  
                model.Resource.package_id == model.Package.id
            ).join(
                model.Group,  
                model.Package.owner_org == model.Group.id
            ).filter(
                func.date(model.Resource.created) >= start_date,
                func.date(model.Resource.created) < end_date,
                model.Package.name.in_(package_name) if data_dict['package_name'] != [""] else True,
                model.Group.name.in_(organizations) if data_dict['organizations'] != [""] else True,
            ).group_by(
                model.Resource.name,
                model.Resource.id,
                func.date(model.Resource.created),
                model.Resource.url,         
                model.Package.name,
                model.Package.id,           
                model.Group.name,
                model.Resource.format
            ).order_by(
                model.Resource.created
            )

            result = query.all()
            
        except Exception as e:
            raise ValidationError(f"database query error: {e}")
        
        return result