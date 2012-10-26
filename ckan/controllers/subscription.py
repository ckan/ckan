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
        definition = {}
        definition['query'] = ''
        if 'q' in request.params:
            definition['query'] = str(urllib.unquote(request.params['q']))
        
        definition['filters'] = {}
        for (param, value) in request.params.items():
            if param in ['tags', 'res_format', 'groups', 'organizations', 'topic', 'location', 'time']:
                if param not in definition['filters']:
                    definition['filters'][param] = [urllib.unquote(value)]
                else:
                    definition['filters'][param].append(urllib.unquote(value))
        definition['type'] = 'search'
        definition['data_type'] = 'dataset'
            
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True}
        data_dict = {'subscription_definition': definition,
                     'subscription_name': request.params['subscription_name']}

        subscription = get_action('subscription_create')(context, data_dict)

        return h.redirect_to(controller='subscription', action='show', subscription_name=subscription['name'])


    def show(self, id=None, subscription_name=None):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True}
        data_dict = {'id': id, 'user_obj': c.userobj, 'subscription_name': subscription_name}

        self._setup_template_variables(context, data_dict)

        if c.subscription['definition']['type'] in ['search']:
            get_action('subscription_item_list_update')(context, data_dict)
            c.subscription_items = get_action('subscription_item_list')(context, data_dict)
            c.added_subscribed_datasets = [item['data'] for item in c.subscription_items if item['status'] == 'added']
            c.changed_subscribed_datasets = [item['data'] for item in c.subscription_items if item['status'] == 'changed']
            c.removed_subscribed_datasets = [item['data'] for item in c.subscription_items if item['status'] == 'removed']
            c.accepted_subscribed_datasets = [item['data'] for item in c.subscription_items if item['status'] == 'accepted']
            c.to_be_accepted = len(c.subscription_items) != len(c.accepted_subscribed_datasets)


            url = h.url_for(controller='package', action='search')
            url += '?q=' + urllib.quote_plus(c.subscription['definition']['query'])

            filters = {}
            for filter_name, filter_value_list in c.subscription['definition']['filters'].iteritems():
                for filter_value in filter_value_list:
                    url += '&' + filter_name + '=' + urllib.quote_plus(filter_value)

            return h.redirect_to(str(url))

        return render('subscription/index.html')
       

    def show_my_datasets(self, id=None):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True}
        data_dict = {'id': id, 'user_obj': c.userobj}
        self._setup_template_variables(context, data_dict)

        return render('subscription/my_datasets.html')
        
               
    def show_dataset_followees(self, id=None):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True}
        data_dict = {'id': id, 'user_obj': c.userobj}
        self._setup_template_variables(context, data_dict)
        dataset_followee_list = get_action('dataset_followee_list')
        c.dataset_followees = dataset_followee_list(context, {'id': c.user_dict['id']})

        return render('subscription/dataset_followees.html')
        
        
    def show_user_followees(self, id=None):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True}
        data_dict = {'id': id, 'user_obj': c.userobj}
        self._setup_template_variables(context, data_dict)
        user_followee_list = get_action('user_followee_list')
        c.user_followees = user_followee_list(context, {'id': c.user_dict['id']})

        return render('subscription/user_followees.html')

               
    def edit(self, subscription_name):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True}
        data_dict = {'subscription_name': subscription_name,
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

