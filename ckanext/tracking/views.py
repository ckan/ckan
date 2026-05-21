"""Flask routes for the tracking extension.

Browsers POST page-views to /_tracking. 
Flask must have a registered route for that path or it returns 405 before middleware runs. 
Recording is done in ckanext.tracking.middleware.track_request, not in this view.
"""

from flask import Blueprint

tracking_bp = Blueprint('tracking', __name__)

def tracking_endpoint():
    return '', 200

tracking_bp.add_url_rule(
    '/_tracking',
    'tracking',
    tracking_endpoint,
    methods=['POST']
)