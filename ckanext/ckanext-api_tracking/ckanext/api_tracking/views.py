from datetime import datetime
from typing import cast
from ckan.types import Context
from flask import Blueprint, request, render_template
import ckan.plugins.toolkit as toolkit
from ckanext.api_tracking.logic.actions import tracking_by_user  # Thay your_package_name bằng tên package thực tế của bạn
from ckan.common import _, current_user
tracking_blueprint = Blueprint('tracking_blueprint', __name__)

def get_statistical_date():
    # Tạo context cho template
    context = {
            'for_view': True,
            'user': current_user.name,
            'auth_user_obj': current_user
        }

        # Chuẩn bị data_dict từ request
    data_dict = {
            'user_obj': current_user,
            'start_date': request.args.get('start_date', ''),
            'end_date': request.args.get('end_date', ''),
            'user_name': request.args.getlist('user_name') or ["", ],  # Giá trị mặc định là một danh sách rỗng
            'package_name': request.args.getlist('package_name') or ["", ],  # Giá trị mặc định là một danh sách rỗng
            'include_resources': True
        }
    # Gọi action để lấy dữ liệu tracking
    try:
        print("111111111111111111111111111111111", data_dict)
        urls_and_counts = toolkit.get_action('tracking_by_user')(context, data_dict)
        print(22222222222222222222222222222222222222, urls_and_counts)
    except toolkit.ValidationError as e:
        # Xử lý lỗi xác thực nếu cần
        print("Validation error:", e)
        urls_and_counts = []  # Hoặc một thông điệp lỗi

    # Render template với dữ liệu đã chuẩn bị
    return render_template('ckanext/stats/index.html', urls_and_counts=urls_and_counts, context=context)


tracking_blueprint.add_url_rule(
    "/dashboard/statistical", view_func=get_statistical_date)

def get_blueprints():
    return [tracking_blueprint]
    
