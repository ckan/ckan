# encoding: utf-8

"""Pylons application test package

When the test runner finds and executes tests within this directory,
this file will be loaded to setup the test environment.

It registers the root directory of the project in sys.path and
pkg_resources, in case the project hasn't been installed with
setuptools.
"""

import ckan.lib.helpers as h
import ckan.model as model

# evil hack as url_for is passed out
url_for = h.url_for

__all__ = [
    "url_for",
    "call_action_api",
]


def is_search_supported():
    is_supported_db = not model.engine_is_sqlite()
    return is_supported_db


class StatusCodes:
    STATUS_200_OK = 200
    STATUS_201_CREATED = 201
    STATUS_400_BAD_REQUEST = 400
    STATUS_403_ACCESS_DENIED = 403
    STATUS_404_NOT_FOUND = 404
    STATUS_409_CONFLICT = 409


def call_action_api(app, action, apikey=None, status=200, **kwargs):
    """POST an HTTP request to the CKAN API and return the result.

    Any additional keyword arguments that you pass to this function as **kwargs
    are posted as params to the API.

    Usage:

        package_dict = post(app, 'package_create', apikey=apikey,
                name='my_package')
        assert package_dict['name'] == 'my_package'

        num_followers = post(app, 'user_follower_count', id='annafan')

    If you are expecting an error from the API and want to check the contents
    of the error dict, you have to use the status param otherwise an exception
    will be raised:

        error_dict = post(app, 'group_activity_list', status=403,
                id='invalid_id')
        assert error_dict['message'] == 'Access Denied'

    :param app: the test app to post to

    :param action: the action to post to, e.g. 'package_create'
    :type action: string

    :param apikey: the API key to put in the Authorization header of the post
        (optional, default: None)
    :type apikey: string

    :param status: the HTTP status code expected in the response from the CKAN
        API, e.g. 403, if a different status code is received an exception will
        be raised (optional, default: 200)
    :type status: int

    :param **kwargs: any other keyword arguments passed to this function will
        be posted to the API as params

    :returns: the 'result' or 'error' dictionary from the CKAN API response
    :rtype: dictionary

    """
    response = app.post(
        "/api/action/{0}".format(action),
        json=kwargs,
        extra_environ={"Authorization": str(apikey)},
        status=status,
    )
    assert (
        "/api/3/action/help_show?name={0}".format(action)
        in response.json["help"]
    )

    if status in (200,):
        assert response.json["success"] is True
        return response.json["result"]
    else:
        assert response.json["success"] is False
        return response.json["error"]
