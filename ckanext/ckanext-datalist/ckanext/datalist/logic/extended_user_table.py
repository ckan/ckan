import datetime
from sqlalchemy import func, literal
import ckan.model as model
import ckan.model.meta as meta
from ckan.plugins.toolkit import ValidationError

class ExtendedUserTable(model.User):

    @classmethod
    def get_users_statistics(cls, data_dict):
        
        start_date = data_dict.get('start_date')
        end_date = data_dict.get('end_date') + datetime.timedelta(days=1)
        sys_admin = data_dict['sys_admin']
        active_date = (datetime.datetime.now() - datetime.timedelta(days=int(data_dict['recent_active_days']))).strftime('%Y-%m-%d')
        
        try: 
            query = meta.Session.query(
                model.User.name,
                model.User.about,
                model.User.email,
                model.User.sysadmin.label('sys_admin'),
                func.date(model.User.created).label('created_date'),
                func.date(model.User.last_active).label('last_active'),
            ).filter(
                func.date(model.User.created) >= start_date,
                func.date(model.User.created) < end_date,
                model.User.sysadmin == sys_admin if sys_admin != [""] else True,
                func.date(model.User.last_active) >= active_date if data_dict['recent_active_days'] != -1 else True,
            ).group_by(
                model.User.name,
                model.User.about,
                model.User.email,
                model.User.sysadmin,
                func.date(model.User.created),
                func.date(model.User.last_active),
            ).order_by(
                func.date(model.User.created)
            )
            
            result = query.all()
            
        except Exception as e:
            raise ValidationError("database query error: {e}" )
        
        return result