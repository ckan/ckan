from flask import Blueprint


statistical_org = Blueprint(
    "statistical_org", __name__)


def page():
    return "Hello, statistical_org!"


statistical_org.add_url_rule(
    "/statistical_org/page", view_func=page)


def get_blueprints():
    return [statistical_org]
