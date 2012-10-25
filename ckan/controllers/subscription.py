import json
import logging
from pylons import session
from pylons.controllers.util import redirect

import genshi
from urllib import quote

import ckan.misc
import ckan.lib.i18n
from ckan.lib.base import *
from ckan.lib import mailer
from ckan.authz import Authorizer
from ckan.lib.navl.dictization_functions import DataError, unflatten
from ckan.logic import NotFound, NotAuthorized, ValidationError
from ckan.logic import check_access, get_action
from ckan.logic import tuplize_dict, clean_dict, parse_params
from ckan.logic.schema import user_new_form_schema, user_edit_form_schema
from ckan.lib.captcha import check_recaptcha, CaptchaError

log = logging.getLogger(__name__)


class SubscriptionController(BaseController):

    def __before__(self, action, **env):
        BaseController.__before__(self, action, **env)
        try:
            context = {'model': model, 'user': c.user or c.author}
            check_access('site_read', context)
        except NotAuthorized:
            if c.action not in ('login', 'request_reset', 'perform_reset',):
                abort(401, _('Not authorized to see this page'))


    def _setup_template_variables(self, context, data_dict):
        c.is_sysadmin = Authorizer().is_sysadmin(c.user)
        try:
            user_dict = get_action('user_show')(context, data_dict)
        except NotFound:
            h.redirect_to(controller='user', action='login', id=None)
        except NotAuthorized:
            abort(401, _('Not authorized to see this page'))
        data_dict['id'] = user_dict['id']
        c.user_dict = user_dict
        c.is_myself = user_dict['name'] == c.user

        try:
            c.subscriptions = get_action('subscription_list')(context, data_dict)
        except NotFound:
            h.redirect_to(controller='subscription', action='index')
        except NotAuthorized:
            abort(401, _('Not authorized to see this page'))

        if data_dict.has_key('subscription_name'):
            try:
                c.subscription = get_action('subscription')(context, data_dict)
            except NotFound:
                h.redirect_to(controller='subscription', action='index')
            except NotAuthorized:
                abort(401, _('Not authorized to see this page'))


    def index(self, id=None):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True}
        data_dict = {'id': id, 'user_obj': c.userobj}
        self._setup_template_variables(context, data_dict)

        return render('subscription/index.html')


    def create(self, id=None):
        print request.params
        definition = {}
        definition['q'] = ''
        if 'q' in request.params:
            definition['q'] = request.params['q']
        
        definition['fq'] = [(param, value) for (param, value) in request.params.items() if param not in ['q', 'page', 'sort', 'subscription_data_type', 'subscription_definition_type', 'subscription_name']]

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True}
        data_dict = {'subscription_data_type': request.params['subscription_data_type'],
                     'subscription_definition_type': request.params['subscription_definition_type'],
                     'subscription_definition': definition,
                     'subscription_name': request.params['subscription_name']}

        subscription = get_action('subscription_create')(context, data_dict)

        return h.redirect_to(controller='subscription', action='show', subscription_name=subscription['name'])


    def show(self, id=None, subscription_name=None):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True}
        data_dict = {'id': id, 'user_obj': c.userobj, 'subscription_name': subscription_name}
        self._setup_template_variables(context, data_dict)

        if c.subscription['definition_type'] in ['search']:
            get_action('subscription_item_list_update')(context, data_dict)
            c.subscription_items = get_action('subscription_item_list')(context, data_dict)
            c.added_subscribed_datasets = [item['data'] for item in c.subscription_items if item['status'] == 'added']
            c.changed_subscribed_datasets = [item['data'] for item in c.subscription_items if item['status'] == 'changed']
            c.removed_subscribed_datasets = [item['data'] for item in c.subscription_items if item['status'] == 'removed']
            c.accepted_subscribed_datasets = [item['data'] for item in c.subscription_items if item['status'] == 'accepted']
            c.to_be_accepted = len(c.subscription_items) != len(c.accepted_subscribed_datasets)


            c.subscription['definition']['fq'] = dict([(fq[0], fq[1]) for fq in c.subscription['definition']['fq']])


            param = {}
            param['controller'] = 'package'
            param['action'] = 'search'
            param['q'] = c.subscription['definition']['q']
            param.update(c.subscription['definition']['fq'])

            return h.redirect_to(**param)

        return render('subscription/index.html')
       
        
    def show_user_followees(self, id=None):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True}
        data_dict = {'id': id, 'user_obj': c.userobj}
        self._setup_template_variables(context, data_dict)
        user_followee_list = get_action('user_followee_list')
        c.user_followees = user_followee_list(context, {'id': c.user_dict['id']})

        return render('subscription/user_followees.html')


    def show_dataset_followees(self, id=None):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True}
        data_dict = {'id': id, 'user_obj': c.userobj}
        self._setup_template_variables(context, data_dict)
        dataset_followee_list = get_action('dataset_followee_list')
        c.dataset_followees = dataset_followee_list(context, {'id': c.user_dict['id']})

        return render('subscription/dataset_followees.html')
        
               
    def edit(self, subscription_name):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True}
        data_dict = {'subscription_name': subscription_name,
                     'new_subscription_data_type': request.params['subscription_data_type'],
                     'new_subscription_definition_type': request.params['subscription_definition_type'],
                     'new_subscription_definition': request.params['subscription_definition'],
                     'new_subscription_name': request.params['subscription_name']}

        subscription = get_action('subscription_update')(context, data_dict)

        return h.redirect_to(controller='subscription', action='show', subscription_name=subscription['name'])


    def mark_changes_as_seen(self, subscription_name=None):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True}
        data_dict = {'subscription_name': subscription_name}

        get_action('subscription_mark_changes_as_seen')(context, data_dict)

        return h.redirect_to(controller='subscription', action='show', subscription_name=subscription_name)
        
        
    def delete(self, subscription_name):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True}
        data_dict = {'subscription_name': subscription_name}

        get_action('subscription_delete')(context, data_dict)

        return redirect(request.params['return_url'])

