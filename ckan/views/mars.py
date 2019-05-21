# encoding: utf-8
import logging

from flask import Blueprint, abort
from flask.views import MethodView
from paste.deploy.converters import asbool
from six import text_type

import ckan.lib.authenticator as authenticator
import ckan.lib.base as base
import ckan.lib.captcha as captcha
import ckan.lib.helpers as h
import ckan.lib.mailer as mailer
import ckan.lib.navl.dictization_functions as dictization_functions
import ckan.logic as logic
import ckan.logic.schema as schema
import ckan.model as model
import ckan.plugins as plugins
from ckan.controllers.home import CACHE_PARAMETERS
from ckan import authz
from ckan.common import _, config, g, request

import ckan.lib.search as search

import ckan.lib.app_globals as app_globals

# hooks for subclasses
new_request_form = u'mars/snippets/access_form_body.html'

mars = Blueprint(u'mars', __name__)
log = logging.getLogger(__name__)

get_action = logic.get_action


@mars.before_request
def before_request():
    u'''set context and check authorization'''
    pass


def index():
    u'''display mars page'''
    pass


# def new(self, data=None, errors=None, error_summary=None):
#     u''' add new record to access request logging table'''

#     data = data or {'from_email': 'aaa@aa.ca'}

#     log.info('MaRS view, fn new, data.from: %s' % data.from_email)

#     return


def _new_form_to_db_schema():
    return schema.reqaccess_new_form_schema()

class ReqAccessView(MethodView):

    def _prepare(self):
        log.info('mars.py, ReqAccessView, _prepare')

        context = {
            u'model': model,
            u'session': model.Session,
            u'schema': _new_form_to_db_schema(),
            u'save': u'save' in request.form
        }

        return context

    def post(self):
        log.info('POST !!! mars.py, ReqAccessView: %s' % request.params)

        context = self._prepare()
        data1 = None

        # a.s.
        data = request.form

        if 'save' in data:
            log.info('mars view 124, save is in data')

            try:
                data_dict = logic.clean_dict(
                    dictization_functions.unflatten(
                        logic.tuplize_dict(logic.parse_params(request.form))))
            except dictization_functions.DataError:
                base.abort(400, _(u'Integrity Error'))


            context[u'message'] = data_dict.get(u'log_message', u'')

            log.info('POST !!! data_dict: %s' % data_dict)

            try:
                logic.get_action(u'reqaccess_create')(context, data_dict)
            except logic.ValidationError as e:
                errors = e.error_dict
                error_summary = e.error_summary
                return self.get(data_dict, errors, error_summary)

            h.flash_success(
                _(u'Request Access saved into database "%s" '
                    ) % (data_dict[u'user_email']))

            return base.render(u'home/index.html')


    def get(self, data=None, errors=None, error_summary=None):
        log.info('GET !!! mars.py, ReqAccessView: %s' % request.params)

        self._prepare()

        user_email = g.userobj.email if g.userobj and g.userobj.email else u'your_email@domain.com'
        maintainer_email = request.params.get('maintainer_email', u'')
        maintainer_name = request.params.get('maintainer_name', u'')

        errors = errors or {}
        error_summary = error_summary or {}

        data = data or {
            'subject': u'AVIN Data Request',
            'maintainer_email': maintainer_email,
            'maintainer_name': maintainer_name,
            'user_email': user_email,
            'user_msg': '',
            'title': u'Title',
        }


        form_vars = {
            u'data': data or {},
            u'errors': errors or {},
            u'error_summary': error_summary or {}
        }

        extra_vars = {
            u'form': base.render(new_request_form, form_vars),
            u'data': data,
            u'errors': errors,
            u'error_summary': error_summary,
        }

        log.info('NEW GET !!! mars.py, ReqAccessView: %s %s %s' % (extra_vars, form_vars, data) )

        return base.render(u'mars/access_form.html', extra_vars)

mars_rules = [
    (u'/', index),
]

for rule, view_func in mars_rules:
    mars.add_url_rule(rule, view_func=view_func)


mars.add_url_rule(u'/marsdataaccess',
                  view_func=ReqAccessView.as_view(str(u'marsdataaccess')))
