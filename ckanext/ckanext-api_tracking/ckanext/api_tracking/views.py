from flask import Blueprint, request, render_template
import requests


tracking_blueprint = Blueprint('api_tracking', __name__)


def get_tracking_view():
    print(11111111111111111111111111)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # Gọi API để lấy dữ liệu
    api_url = "http://127.0.0.1:5000/api/3/action/tracking_by_user"
    print(api_url)
    
    params = {
        'start_date': start_date,
        'end_date': end_date
    }
    response = requests.get(api_url, params=params)
    print(response)
    print(22222222)

    if response.status_code == 200:
        data = response.json().get('result.tracking', [])
        print(data)
    else:
        data = []

    return render_template('user/dashboard_statistical.html', data=data)

tracking_blueprint.add_url_rule(u'/aaa', view_func=get_tracking_view)
def get_blueprints():
    return [tracking_blueprint]