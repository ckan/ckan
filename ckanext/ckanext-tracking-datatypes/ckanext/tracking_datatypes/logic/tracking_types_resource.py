import datetime
from ckan.plugins.toolkit import ValidationError
import ckan.model.meta as meta
import ckan.model as model
from sqlalchemy import func


class TrackingAPI:
    @classmethod
    def get_resource_access_count_by_date(cls, data_dict, limit, offset):
        """
        API theo dõi số lượng truy cập từng loại resource theo ngày.

        :param data_dict: Dictionary chứa thông tin đầu vào, yêu cầu `tracking_date`.
        :return: JSON chứa thông tin về các loại resource và số lượt truy cập.
        """
        start_date = data_dict.get('start_date')
        end_date = data_dict.get('end_date') + datetime.timedelta(days=1)
        try:
            query = meta.Session.query(
                model.tracking_raw_table.c.tracking_type,
                model.tracking_raw_table.c.url,
                model.Resource.format.label('resource_format'),
                func.date(model.tracking_raw_table.c.access_timestamp).label('date'),
                func.count(model.tracking_raw_table.c.url).label('access_count')
            ).join(
                model.Resource,
                func.split_part(model.tracking_raw_table.c.url, '/', -1) == model.Resource.id
            ).filter(
                model.tracking_raw_table.c.access_timestamp >= start_date,
                model.tracking_raw_table.c.access_timestamp < end_date
            ).group_by(
                model.tracking_raw_table.c.tracking_type,
                model.tracking_raw_table.c.url,
                model.Resource.format,
                func.date(model.tracking_raw_table.c.access_timestamp)
            ).limit(limit).offset(offset).all()

            # Đóng gói kết quả trả về dưới dạng JSON
            result = []
            print("đây là query", query)
            for row in query:
                result.append({
                    'tracking_type': row.tracking_type,
                    'date': row.date,
                    'format': row.resource_format,
                    'access_count': row.access_count
                }) 

            return result

        except Exception as e:
            raise ValidationError(f"Error fetching resource access count: {e}")
