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
        format_type = data_dict.get('format_type')
        try:
            query = meta.Session.query(
              model.Resource.format.label('format_type'),
                func.count(model.tracking_raw_table.c.url).label('total_access'),
                model.Resource.id.label('resource_id'),
                model.Resource.name.label('resource_name'),
                func.date(model.Resource.created).label('date'),
                func.date(model.tracking_raw_table.c.access_timestamp).label('date_updated'),
                func.count(model.tracking_raw_table.c.url).label('resource_access_count')
            ).join(
                model.Resource,
                func.split_part(model.tracking_raw_table.c.url, '/', -1) == model.Resource.id
            ).filter(
                model.tracking_raw_table.c.access_timestamp >= start_date,
                model.tracking_raw_table.c.access_timestamp < end_date
            )
            
            if format_type:
                query = query.filter(func.lower(model.Resource.format).ilike(func.lower(format_type)))
            query = query.group_by(
                model.Resource.format,
                model.Resource.id,
                model.Resource.name,
                model.Resource.created,
                model.tracking_raw_table.c.access_timestamp
            ).limit(limit).offset(offset).all()

            # Đóng gói kết quả trả về dưới dạng JSON
            format_group = {}
            for row in query:
                format_type = row.format_type
                if format_type not in format_group:
                    format_group[format_type] = {
                        "format_type": format_type,
                        "total_access": 0,
                        "resources": []
                    }
                    
                existing_resource = next((res for res in format_group[format_type]["resources"] if res["id"] == row.resource_id), None)

                if existing_resource:
                    # Cập nhật tổng lượt truy cập cho tài nguyên đã có
                    existing_resource["total_access"] += row.resource_access_count
                else:
                    # Nếu chưa có tài nguyên, thêm vào resources
                    format_group[format_type]["resources"].append({
                        "id": row.resource_id,
                        "resource_name": model.Resource.get(row.resource_id).name,
                        "date_created": row.date,
                        "date_updated": row.date_updated,
                        "total_access": row.resource_access_count
                    })

                # Cập nhật tổng lượt truy cập của format_type
                format_group[format_type]["total_access"] += row.resource_access_count

            return list(format_group.values())

        except Exception as e:
            raise ValidationError(f"Error fetching resource access count: {e}")