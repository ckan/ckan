import datetime
from sqlalchemy import func, literal
from ckanext.activity.model.activity import Activity
import ckan.model.meta as meta
from ckan.plugins.toolkit import ValidationError

class ExtendedActivityTable(Activity):

    @classmethod
    def get_login_activity_stats(cls, data_dict):
        try:        
            results = [2]
            query = meta.Session.query(cls.id, func.date_trunc('second', cls.timestamp).label('login_time'), cls.user_id, cls.data
                                    ).filter(cls.activity_type == 'login_success'
                                    ).order_by(func.date_trunc('second', cls.timestamp))      
                                    
            if data_dict.get('start_date') and data_dict.get('end_date'):
                start_date = data_dict.get('start_date')
                end_date = data_dict.get('end_date') + datetime.timedelta(days=1)
                query = query.filter(func.date(cls.timestamp) >= start_date, func.date(cls.timestamp) < end_date)
                  
            results = query.all()
            user_tracking_data = {}
            
            try:
                user_count = 0
                for row in results:
                    user_name = row.data.get('username', None)
                    user_id = row.user_id
                    
                    if user_id not in user_tracking_data:
                        user_count+=1
                        user_tracking_data[user_id] = {
                            'user_name': user_name,
                            'login_total': 0,
                            'login_history': []
                        }
                    user_tracking_data[user_id]['login_total'] += 1

                    user_tracking_data[user_id]['login_history'].append({
                        'login_time': row.login_time.strftime('%H:%M:%S %Y-%m-%d'),
                        # 'id': row.id, 
                        'login_detail': row.data if data_dict.get('login_detail') else []
                    })
                
                results = {
                    'total_user_login': user_count,
                    'total_login': query.count(),
                    'login_activity': list(user_tracking_data.values())
                }
            except Exception as e:
                raise ValidationError(f"Error processing results: {e}")
            
        except Exception as e:
            raise ValidationError(f"database query error: {e}" )
        return results