import logging

import ckan.model as model
import ckan.logic as logic
from ckan.common import json, _, ungettext, c

from flask import abort, jsonify, request, Response, url_for
from flask.views import MethodView

log = logging.getLogger(__name__)


class ApiView(MethodView):

    def get(self, func_name):
        params = request.args.copy()
        return self._make_request(func_name, params)

    def post(self, func_name):
        data = request.get_json(force=True)
        return self._make_request(func_name, data)

    def _make_request(self, func_name, data):
        try:
            fn = logic.get_action(func_name)
        except Exception, e:
            abort(404)

        help = url_for('api',func_name="help_show", _external=True)
        help = help + "?name={0}".format(func_name)

        context = {'model':model, 'session': model.Session, 'user': c.user}
        try:
            response = fn(context, data)
        except logic.NotFound, nfe:
            error_dict = {
                '__type': 'Not Found Error',
                'message': 'Not found'
            }

            return_dict = {
                'error': error_dict,
                'success': False
            }

            log.info('Not Found error (Action API): %r' % str(nfe))
            return jsonify(return_dict), 404
        except logic.NotAuthorized, not_auth:
            return_dict = {
                'success': False,
                'error': {
                    '__type': 'Not Authorized Error',
                    'message': 'Not Authorized'
                }
            }

            log.info('Not Authorized error (Action API): %r' % str(not_auth))
            return jsonify(return_dict), 403
        except logic.ValidationError, e:
            error_dict = e.error_dict
            error_dict['__type'] = 'Validation Error'
            return_dict = {
                'error': error_dict,
                'success': False
            }

            log.info('Validation error (Action API): %r' % str(e.error_dict))
            return jsonify(return_dict), 409

        if isinstance(response, list):
            # Add help url
            response = {
                "success": True,
                "result": response
            }
        if isinstance(response, basestring):
            # Add help url
            response = {
                "success": True,
                "result": response
            }

        response['help'] = help

        return jsonify(response)

