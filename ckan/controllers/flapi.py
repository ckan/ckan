import logging
import json

import ckan.model as model
import ckan.logic as logic

from flask import abort, jsonify, request, Response
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

        context = {'model':model, 'session': model.Session, 'user': ''}
        try:
            response = fn(context, params)
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
            # Flask won't allow jsonifying lists because it's unsafe. Apparently.
            return Response(json.dumps(response),  mimetype='application/json')

        return jsonify(response)

    def post(self, func_name):
        print "A POST request to", func_name
        return "!"


