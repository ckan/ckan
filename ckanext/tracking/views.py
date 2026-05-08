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