from typing import Any
from flask import Blueprint, request
import ckan.plugins.toolkit as toolkit
from ckan.common import current_user
import ckanext.api_tracking.logic.auth as auth  # Thay bằng tên extension thực tế của bạn
from datetime import datetime
from ckan import logic
import ckan.lib.base as base

# Blueprint for tracking
dashboard = Blueprint('tracking_blueprint', __name__, url_prefix=u'/dashboard')

def statistical():
    # Get query parameters
    q = request.args.get('q', '')
    today = datetime.today().date()
    start_date = request.args.get('start_date', str(today))
    end_date = request.args.get('end_date', str(today))
    package_name = [name.strip() for name in request.args.get('package_name', '').split(',')]
    include_resources = request.args.get('include_resources') == 'on'
    user_name = request.args.getlist('user_name') or [""]
    is_admin = current_user.sysadmin

    # Check access rights
    try:
        logic.check_access('tracking_by_user', {})
    except logic.NotAuthorized:
        return base.abort(403, toolkit._('Need to be system administrator to administer'))

    # Fetch tracking data based on admin status
    try:
        action = 'tracking_by_user' if is_admin else 'tracking_urls_and_counts'
        urls_and_counts = logic.get_action(action)(data_dict={
            u'q':q,
            'user_name': user_name,
            'start_date': start_date,
            'end_date': end_date,
            'package_name': package_name,
            'include_resources': include_resources,
            })  # type: ignore
    except logic.ValidationError as e:
        urls_and_counts = []

    # Prepare variables for rendering
    extra_vars: dict[str, Any] = {
        'urls_and_counts': urls_and_counts,
        'start_date': start_date,
        'end_date': end_date,
        'package_name': package_name,
        'include_resources': include_resources,
        'is_admin': is_admin
    }
    
    if isinstance(urls_and_counts, dict):
        error_message = urls_and_counts.get('error', None)
        if error_message:
            extra_vars[u'error'] = error_message
        else:
            extra_vars[u'q'] = urls_and_counts.get('q')
            extra_vars[u'start_time'] = urls_and_counts.get('start_time')
            extra_vars[u'end_time'] = urls_and_counts.get('end_time')
            extra_vars[u'package_name'] = urls_and_counts.get('package_name')
            extra_vars[u'include_resources'] = urls_and_counts.get('include_resources')
    elif isinstance(urls_and_counts, list):
        # Handle the case when urls_and_counts is a list
        extra_vars[u'list_data'] = urls_and_counts

    

    # Render the template with the prepared variables
    return base.render('user/dashboard_statistical.html', extra_vars)

# Register route for blueprint
dashboard.add_url_rule(
    u"/statistical", view_func=statistical, methods=['GET',]
)

def get_blueprints():
    return [dashboard]
