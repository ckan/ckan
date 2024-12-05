from ckan.plugins.toolkit import ValidationError
import ckan.model.meta as meta
import ckan.model as model
from sqlalchemy import func, case

class OrganizationStatisticsAPI:
    @classmethod
    def get_organization_package_status(cls, data_dict):
        """
        API thống kê số lượng gói theo trạng thái và chi tiết package của tổ chức.

        :param data_dict: Dictionary chứa `organization_name`, `private`, `state`, `include_datasets`.
        :return: JSON chứa thông tin số lượng gói theo `state` và thông tin chi tiết về `package` của tổ chức.
        """
        organization_name = data_dict.get('organization_name')  # Sử dụng tên tổ chức thay vì id_org
        private = data_dict.get('private')
        state = data_dict.get('state')
        include_datasets = data_dict.get('include_datasets', False)

        try:
            # Truy vấn cơ bản lấy số liệu thống kê
            query = meta.Session.query(
                model.Group.name.label('organization_name'),
                model.Package.state.label('package_state'),
                func.count(model.Package.id).label('state_count'),
                func.sum(case([(model.Package.private == False, 1)], else_=0)).label('public_count'),
                func.sum(case([(model.Package.private == True, 1)], else_=0)).label('private_count')
            ).outerjoin(
                model.Package, model.Package.owner_org == model.Group.id
            ).filter(
                model.Group.is_organization == True
            )

            if organization_name:
                query = query.filter(model.Group.name == organization_name)

            if private is not None:
                query = query.filter(model.Package.private == private)

            if state:
                query = query.filter(model.Package.state == state)

            query = query.group_by(
                model.Group.name,
                model.Package.state
            ).all()
            
            print("======================>query",query)

            # Danh sách kết quả trả về
            result = []

            # Duyệt qua các kết quả truy vấn và thêm vào result
            for row in query:
                result.append({
                    'organization_name': row.organization_name,
                    'package_state': row.package_state or "no state",
                    'state_count': row.state_count,
                    'public_count': row.public_count,
                    'private_count': row.private_count,
                    'datasets': []  # Nếu cần, bạn có thể thêm các package chi tiết ở đây
                })

            # Nếu include_datasets là True, thêm chi tiết package
            if include_datasets:
                dataset_query = meta.Session.query(
                    model.Package.id.label('package_id'),
                    model.Package.title.label('package_name'),
                    model.Package.state.label('package_state'),
                    model.Package.private.label('is_private'),
                    model.Package.metadata_modified.label('package_created'),
                    model.Group.name.label('organization_name')
                ).join(
                    model.Group, model.Package.owner_org == model.Group.id
                ).filter(
                    model.Group.is_organization == True
                )

                if organization_name:
                    dataset_query = dataset_query.filter(model.Group.name == organization_name)

                if private is not None:
                    dataset_query = dataset_query.filter(model.Package.private == private)

                if state:
                    dataset_query = dataset_query.filter(model.Package.state == state)

                # Thêm chi tiết datasets vào các kết quả
                for row in dataset_query.all():
                    for org_result in result:
                        if org_result['organization_name'] == row.organization_name and org_result['package_state'] == (row.package_state or "no state"):
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
