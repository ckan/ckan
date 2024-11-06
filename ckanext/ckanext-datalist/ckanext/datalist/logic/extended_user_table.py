import datetime
from sqlalchemy import func, literal
import ckan.model as model
import ckan.model.meta as meta
from ckan.plugins.toolkit import ValidationError

class ExtendedUserTable(model.User):

    @classmethod
    def get_users_statistics(cls, data_dict):
        try:        
            results = []
            query = meta.Session.query(cls.name, cls.about, cls.email, cls.sysadmin.label('sys_admin'),
                                       func.date(cls.created).label('created_date'), func.date(cls.last_active).label('last_active'),)
            
            if data_dict.get('start_created_date') and data_dict.get('end_created_date'):
                start_date = data_dict.get('start_created_date')
                end_date = data_dict.get('end_created_date') + datetime.timedelta(days=1)
                query = query.filter(func.date(cls.created) >= start_date, func.date(cls.created) < end_date)
                
            if 'sys_admin' in data_dict:
                query = query.filter(cls.sysadmin == data_dict.get('sys_admin'))
            if data_dict.get('target_active_date'):
                target_active_date = data_dict.get('target_active_date')
            else: 
                target_active_date = datetime.datetime.now()
                  
            active_date = (target_active_date - 
                            datetime.timedelta(days=int(data_dict['recent_active_days']))).strftime('%Y-%m-%d')
            query = query.filter(func.date(cls.last_active) >= active_date, func.date(cls.last_active) <= target_active_date)
            query = query.group_by(cls.name, cls.about, cls.email, cls.sysadmin, func.date(cls.created), func.date(cls.last_active),)
            query = query.order_by(func.date(cls.created))
            
            try:
                result = []
                count = 0
                for row in range(data_dict.get('recent_active_days')):
                    date = (target_active_date - datetime.timedelta(days=row)).strftime('%Y-%m-%d')
                    result.append({
                        'date': date,
                        'active_user_count': query.filter(func.date(cls.last_active) == date).count(),
                        'user_info_detail': query.filter(func.date(cls.last_active) == date).all() if data_dict.get('include_user_info_detail') else None
                    })    
                    count += query.filter(func.date(cls.last_active) == date).count()
            except Exception as e:
                raise ValidationError(f"Error processing results: {e}")
            
            target_active_date = target_active_date.strftime('%Y-%m-%d')
            results = {
                'total_user_count': count,
                'days': result
            }
        except Exception as e:
            raise ValidationError(f"database query error: {e}" )
        return results