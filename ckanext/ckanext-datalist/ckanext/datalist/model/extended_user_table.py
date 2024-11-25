import datetime
from sqlalchemy import func, literal
import ckan.model as model
import ckan.model.meta as meta
from ckan.plugins.toolkit import ValidationError, Invalid

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
    
    @classmethod
    def get_new_users_statistics(cls, data_dict):
        try:        
            results = []
            query = meta.Session.query(cls.name, cls.about, cls.email, cls.state,
                                       func.date(cls.created).label('created_date'),)
            
            if data_dict.get('start_date') and data_dict.get('end_date'):
                start_date = data_dict.get('start_date')
                end_date = data_dict.get('end_date') + datetime.timedelta(days=1)
                query = query.filter(func.date(cls.created) >= start_date, func.date(cls.created) < end_date)
            else: 
                current_date = datetime.datetime.now()
                start_date = current_date
                end_date = current_date + datetime.timedelta(days=1)
                
            if (end_date - start_date).days > 30:
                raise Invalid('The gap between start_date and end_date cannot be greater than 30 days.')
                
            if data_dict.get('state'):
                state = data_dict.get('state')    
                query = query.filter(cls.state == state)
                
            query = query.group_by(cls.name, cls.about, cls.email, cls.sysadmin, func.date(cls.created), cls.state)
            query = query.order_by(func.date(cls.created))
            
            results = query.all()
            
            try: 
                result = []
                count = 0
                delta_days = (end_date - start_date).days
                
                for row in range (delta_days):
                    date = (end_date - datetime.timedelta(days=row) - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
                    result.append({
                        'date': date,
                        'user_created_count': query.filter(func.date(cls.created) == date).count(),
                        'user_info_detail': query.filter(func.date(cls.created) == date).all() if data_dict.get('include_user_info_detail') else None
                    })  
                    count += query.filter(func.date(cls.created) == date).count()
            except Exception as e:
                raise ValidationError(f"database query error: {e}")   
            
            results = {
                'total_user_created_count': count,
                'days': result
            }
            
        except Exception as e:
            raise ValidationError(f"database query error: {e}" )
        return results