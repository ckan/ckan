import math
from typing import Any
from flask import Blueprint, request
import ckan.plugins.toolkit as toolkit
import ckanext.api_tracking.logic.auth as auth 
from datetime import datetime, timedelta
from ckan import logic
import ckan.lib.base as base

dashboard = Blueprint('tracking_blueprint', __name__, url_prefix=u'/dashboard')

def statistical():

    try:
        logic.check_access('user_check', {})
    except logic.NotAuthorized:
        return base.abort(403, toolkit._('Need to be system administrator to administer'))


    start_date = request.args.get('start_date', '2024/11/01')  
    end_date = request.args.get('end_date', '2024/11/30')  
    state = request.args.get('state', 'active')

    try:
        action = 'stats_new_users'
        urls_and_counts = logic.get_action(action)(data_dict={
            u'start_date': start_date,
            u'end_date': end_date,
            u'state': state,
        })

    except logic.ValidationError as e:
        urls_and_counts = []    
    
    extra_vars: dict[str, Any] = {
        u'urls_and_counts': urls_and_counts,
        u'start_date': start_date,
        u'end_date': end_date,
    }

    return base.render('user/dashboard_statistical.html', extra_vars)

dashboard.add_url_rule(
    u"/statistical", view_func=statistical, methods=['GET', 'POST']
)

def get_blueprints():
    return [dashboard]