from flask import Blueprint


tracking_datatypes = Blueprint(
    "tracking_datatypes", __name__)


def page():
    return "Hello, tracking_datatypes!"


tracking_datatypes.add_url_rule(
    "/tracking_datatypes/page", view_func=page)


def get_blueprints():
    return [tracking_datatypes]
