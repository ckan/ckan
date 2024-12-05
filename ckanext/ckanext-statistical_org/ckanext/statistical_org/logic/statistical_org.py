import datetime
from ckan.plugins.toolkit import ValidationError
import ckan.model.meta as meta
import ckan.model as model
from sqlalchemy import func, case
from collections import defaultdict

class OrganizationStatisticsAPI:
    @classmethod
    def get_organization_package_status(cls, data_dict):
        """
        API thống kê số lượng gói theo trạng thái và chi tiết package của tổ chức.

        :param data_dict: Dictionary chứa `id_org`, `private`, `state`, `include_datasets`.
        :return: JSON chứa thông tin số lượng gói theo `state` và thông tin chi tiết về `package`.
        """
        id_org = data_dict.get('id_org')
        private = data_dict.get('private')
        state = data_dict.get('state')
        include_datasets = data_dict.get('include_datasets', False)

        try:
            # Truy vấn cơ bản lấy số liệu thống kê
            query = meta.Session.query(
                model.Group.title.label('organization_name'),
                model.Package.state.label('package_state'),
                func.count(model.Package.id).label('state_count'),
                func.sum(case([(model.Package.private == False, 1)], else_=0)).label('public_count'),
                func.sum(case([(model.Package.private == True, 1)], else_=0)).label('private_count')
            ).outerjoin(
                model.Package, model.Package.owner_org == model.Group.id
            ).filter(
                model.Group.is_organization == True
            )

            if id_org:
                query = query.filter(model.Group.id == id_org)

            if private is not None:
                query = query.filter(model.Package.private == private)

            if state:
                query = query.filter(model.Package.state == state)

            query = query.group_by(
                model.Group.title,
                model.Package.state
            ).all()

            # Đóng gói dữ liệu thống kê theo tổ chức
            organization_stats = defaultdict(lambda: defaultdict(dict))
            for row in query:
                organization_name = row.organization_name
                package_state = row.package_state or "no state"
                organization_stats[organization_name][package_state] = {
                    "state_count": row.state_count,
                    "public_count": row.public_count,
                    "private_count": row.private_count,
                    "datasets": []
                }

            # Nếu include_datasets là True, thêm chi tiết package
            if include_datasets:
                dataset_query = meta.Session.query(
                    model.Package.id.label('package_id'),
                    model.Package.title.label('package_name'),
                    model.Package.state.label('package_state'),
                    model.Package.private.label('is_private'),
                    model.Package.metadata_modified.label('package_created'),
                    model.Group.title.label('organization_name')
                ).join(
                    model.Group, model.Package.owner_org == model.Group.id
                ).filter(
                    model.Group.is_organization == True
                )

                if id_org:
                    dataset_query = dataset_query.filter(model.Group.id == id_org)

                if private is not None:
                    dataset_query = dataset_query.filter(model.Package.private == private)

                if state:
                    dataset_query = dataset_query.filter(model.Package.state == state)

                for row in dataset_query.all():
                    org_name = row.organization_name
                    package_state = row.package_state or "no state"
                    dataset = {
                        "package_id": row.package_id,
                        "package_name": row.package_name,
                        "package_state": package_state,
                        "is_private": row.is_private,
                        "package_created": row.package_created
                    }

                    organization_stats[org_name][package_state]["datasets"].append(dataset)

            # Chuyển đổi kết quả thành JSON
            result = []
            for org_name, states in organization_stats.items():
                result.append({
                    'organization_name': org_name,
                    'states': [
                        {
                            'state': state,
                            'state_count': details['state_count'],
                            'public_count': details['public_count'],
                            'private_count': details['private_count'],
                            'include_datasets': details['datasets'] if include_datasets else []
                        }
                        for state, details in states.items()
                    ]
                })

            return result

        except Exception as e:
            raise ValidationError(f"Error fetching organization package status: {e}")
