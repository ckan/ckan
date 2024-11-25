import datetime
from sqlalchemy import func, literal
import ckan.model as model
import ckan.model.meta as meta
from ckan.plugins.toolkit import ValidationError

class ExtendedResourceTable(model.Resource):

    @classmethod
    def get_resources_statistics(cls, data_dict, limit, offset):
        
        if data_dict.get('start_date'):
            start_date = data_dict.get('start_date')
        else:
            current_date = datetime.datetime.now().strftime('%Y-%m-%d')
            start_date = current_date
    
        if data_dict.get('end_date'):
            end_date = data_dict.get('end_date') + datetime.timedelta(days=1)
        else:
            current_date = datetime.datetime.now().strftime('%Y-%m-%d')
            end_date = datetime.datetime.strptime(current_date, '%Y-%m-%d') + datetime.timedelta(days=1)
        
        try:
            query = meta.Session.query(
                cls.name.label('resource_name'), cls.id.label('resource_id'), cls.format,
                func.date(cls.created).label('created_date'), model.Package.name.label('package_name'), model.Group.name.label('organization'),
                (literal('/dataset/') + model.Package.id + literal('/resource/') + cls.id + literal('/download/') + cls.url).label('download_url'),
            ).join(model.Package, cls.package_id == model.Package.id
            ).join(model.Group, model.Package.owner_org == model.Group.id
            ).filter(func.date(cls.created) >= start_date, func.date(cls.created) < end_date,
            ).group_by(cls.name, cls.id, func.date(cls.created), cls.url, model.Package.name, model.Package.id, model.Group.name, cls.format
            ).order_by(cls.created)
            
            if data_dict.get('organizations'):
                organizations = data_dict['organizations']
                query = query.filter(model.Group.name.in_(organizations))
            if data_dict.get('package_name'):
                package_name = data_dict['package_name']
                query = query.filter(model.Package.name.in_(package_name))
            
            query = query.limit(limit).offset(offset)
            result = query.all()
            
        except Exception as e:
            raise ValidationError(f"database query error: {e}")
        
        return result