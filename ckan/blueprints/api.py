# encoding: utf-8

"""API blueprint - replaces ckan.controllers.api"""

from flask import Blueprint, request, jsonify, g, make_response
import json as json_module
import ckan.logic as logic
import ckan.model as model
import ckan.lib.navl.dictization_functions as df
from ckan.common import _

api = Blueprint('api', __name__)


def _finish_ok(response_data=None, content_type='json', status=200):
    """Return a success response"""
    if content_type == 'json':
        response_data = json_module.dumps(response_data)
        response = make_response(response_data, status)
        response.headers['Content-Type'] = 'application/json;charset=utf-8'
    else:
        response = make_response(response_data, status)
    return response


def _finish_error(error_msg, status=400):
    """Return an error response"""
    response = jsonify({
        'success': False,
        'error': {'__type': 'Error', 'message': error_msg}
    })
    response.status_code = status
    return response


def _get_action_from_request(request):
    """Get the action function name from the request"""
    function_name = request.view_args.get('logic_function')
    if not function_name:
        return None
    try:
        return logic.get_action(function_name)
    except KeyError:
        return None


@api.route('/action/<logic_function>', methods=['GET', 'POST'])
def action(logic_function):
    """Main API action handler

    Handles all logic action API calls (e.g., package_show, package_create, etc.)
    """
    try:
        function = logic.get_action(logic_function)
    except KeyError:
        return _finish_error('Action name not known: %s' % logic_function, 404)

    # Get context
    context = {
        'model': model,
        'session': model.Session,
        'user': g.user,
        'auth_user_obj': getattr(g, 'userobj', None)
    }

    # Get data from request
    if request.method == 'POST':
        if request.is_json:
            data_dict = request.get_json()
        else:
            data_dict = dict(request.form.items())
            # Merge in URL parameters
            data_dict.update(dict(request.args.items()))
    else:
        data_dict = dict(request.args.items())

    # Handle file uploads
    if request.files:
        for key, file in request.files.items():
            data_dict[key] = file

    try:
        # Call the action
        result = function(context, data_dict)

        # Return success response
        return _finish_ok({
            'help': 'api/3/action/%s' % logic_function,
            'success': True,
            'result': result
        })

    except logic.NotFound as e:
        return _finish_error(str(e), 404)
    except logic.NotAuthorized as e:
        return _finish_error(str(e), 403)
    except logic.ValidationError as e:
        error_dict = e.error_dict if hasattr(e, 'error_dict') else {'message': str(e)}
        return _finish_error(error_dict, 400)
    except Exception as e:
        return _finish_error('Internal server error: %s' % str(e), 500)


@api.route('/<path:ver>/action/<logic_function>', methods=['GET', 'POST'])
def action_versioned(ver, logic_function):
    """Versioned API action handler

    Handles API calls with version prefix (e.g., /api/3/action/package_show)
    """
    return action(logic_function)


@api.route('/')
@api.route('/<int:ver>/')
def get_api(ver=3):
    """Get API version information"""
    return _finish_ok({
        'version': ver,
        'description': 'CKAN API version %d' % ver
    })


@api.route('/<int:ver>/search/<register>')
def search(ver, register):
    """Legacy search endpoint"""
    return _finish_error('This API version is deprecated. Please use /api/3/action/package_search', 410)


# Utility endpoints
@api.route('/<int:ver>/util/user/autocomplete')
def user_autocomplete(ver):
    """User autocomplete utility"""
    q = request.args.get('q', '')
    limit = int(request.args.get('limit', 20))

    context = {'model': model, 'session': model.Session, 'user': g.user}
    data_dict = {'q': q, 'limit': limit}

    try:
        users = logic.get_action('user_autocomplete')(context, data_dict)
        return _finish_ok(users)
    except Exception as e:
        return _finish_error(str(e))


@api.route('/<int:ver>/util/dataset/autocomplete')
def dataset_autocomplete(ver):
    """Dataset autocomplete utility"""
    q = request.args.get('q', '')
    limit = int(request.args.get('limit', 10))

    context = {'model': model, 'session': model.Session, 'user': g.user}
    data_dict = {'q': q, 'limit': limit}

    try:
        packages = logic.get_action('package_autocomplete')(context, data_dict)
        return _finish_ok(packages)
    except Exception as e:
        return _finish_error(str(e))


@api.route('/<int:ver>/util/tag/autocomplete')
def tag_autocomplete(ver):
    """Tag autocomplete utility"""
    q = request.args.get('q', '')
    limit = int(request.args.get('limit', 10))

    context = {'model': model, 'session': model.Session, 'user': g.user}
    data_dict = {'q': q, 'limit': limit}

    try:
        tags = logic.get_action('tag_autocomplete')(context, data_dict)
        return _finish_ok(tags)
    except Exception as e:
        return _finish_error(str(e))


@api.route('/<int:ver>/util/status')
def status(ver):
    """API status endpoint"""
    return _finish_ok({
        'site_title': 'CKAN',
        'ckan_version': '2.7.0',
        'site_url': 'http://localhost:5000',
        'site_description': 'CKAN is a tool for making open data websites',
        'error_emails_to': None,
        'locale_default': 'en'
    })
