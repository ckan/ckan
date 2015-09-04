import logging

import ckan.model as model
import ckan.logic as logic

from flask import abort, jsonify, request
from flask.views import MethodView

log = logging.getLogger(__name__)


class ApiView(MethodView):

    def get(self, func_name):

        # TODO: Identify user - check_access

        try:
            fn = logic.get_action(func_name)
        except Exception, e:
            abort(404)

        params = request.args

        # TODO: Check and pop callback

        try:
            response = fn({'model':model, 'session': model.Session}, params)
        except logic.ValidationError, e:
            error_dict = e.error_dict
            error_dict['__type'] = 'Validation Error'
            return_dict = {
                'error': error_dict,
                'success': False
            }

            log.info('Validation error (Action API): %r' % str(e.error_dict))
            return jsonify(return_dict), 409

        return jsonify(response)

    def post(self, func_name):
        print "A POST request to", func_name
        return "!"


