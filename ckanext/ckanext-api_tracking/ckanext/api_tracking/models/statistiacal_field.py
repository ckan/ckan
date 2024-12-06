from ckan.plugins.toolkit import ValidationError
import ckan.model.meta as meta
import ckan.model as model
from sqlalchemy import func, case

class FieldStatisticsAPI:
    @classmethod
    def get_field_package_status(cls, data_dict):
        field_names = data_dict.get('field_name', [])
        
        # Kiểm tra nếu field_names là chuỗi trống hoặc chứa [""] thì bỏ lọc
        if not field_names or (isinstance(field_names, list) and "" in field_names):
            field_names = None

        private = data_dict.get('private')
        state = data_dict.get('state')
        include_datasets = data_dict.get('include_datasets', False)

        try:
            # Truy vấn cơ bản lấy số liệu thống kê
            query = meta.Session.query(
                model.Tag.name.label('field_name'),
                model.Package.state.label('package_state'),
                func.count(model.Package.id).label('state_count'),
                func.sum(case([(model.Package.private == False, 1)], else_=0)).label('public_count'),
                func.sum(case([(model.Package.private == True, 1)], else_=0)).label('private_count')
            ).join(
                model.PackageTag, model.Package.id == model.PackageTag.package_id
            ).join(
                model.Tag, model.Tag.id == model.PackageTag.tag_id
            )

            # Chỉ áp dụng bộ lọc field_names nếu field_names có giá trị hợp lệ
            if field_names:
                query = query.filter(model.Tag.name.in_(field_names))

            if private is not None:
                query = query.filter(model.Package.private == private)

            if state:
                query = query.filter(model.Package.state == state)

            query = query.group_by(
                model.Tag.name,
                model.Package.state
            ).all()

            result = []
            for row in query:
                result.append({
                    'field_name': row.field_name,
                    'package_state': row.package_state or "no state",
                    'state_count': row.state_count,
                    'public_count': row.public_count,
                    'private_count': row.private_count,
                    'datasets': []
                })

            if include_datasets:
                dataset_query = meta.Session.query(
                    model.Package.id.label('package_id'),
                    model.Package.title.label('package_name'),
                    model.Package.state.label('package_state'),
                    model.Package.private.label('is_private'),
                    model.Package.metadata_modified.label('package_created'),
                    model.Tag.name.label('field_name')
                ).join(
                    model.PackageTag, model.Package.id == model.PackageTag.package_id
                ).join(
                    model.Tag, model.Tag.id == model.PackageTag.tag_id
                )

                if field_names:
                    dataset_query = dataset_query.filter(model.Tag.name.in_(field_names))

                if private is not None:
                    dataset_query = dataset_query.filter(model.Package.private == private)

                if state:
                    dataset_query = dataset_query.filter(model.Package.state == state)

                for row in dataset_query.all():
                    for org_result in result:
                        if org_result['field_name'] == row.field_name and org_result['package_state'] == (row.package_state or "no state"):
                            org_result['datasets'].append({
                                "package_id": row.package_id,
                                "package_name": row.package_name,
                                "package_state": row.package_state or "no state",
                                "is_private": row.is_private,
                                "package_created": row.package_created
                            })

            return result

        except Exception as e:
            raise ValidationError(f"Error fetching organization package status: {e}")
