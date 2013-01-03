import json
import logging

import genshi
import ckan.misc
import ckan.lib.i18n
from ckan.lib.base import *
from ckan.lib import mailer
from ckan.authz import Authorizer
from ckan.lib.navl.dictization_functions import DataError, unflatten
from ckan.logic import NotFound, NotAuthorized, ValidationError, ParameterError
from ckan.logic import check_access, get_action
from ckan.logic import tuplize_dict, clean_dict, parse_params
from ckan.logic.schema import user_new_form_schema, user_edit_form_schema
from ckan.lib.captcha import check_recaptcha, CaptchaError
from ckan.plugins import PluginImplementations, ISubscription

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
                c.subscription = get_action('subscription_show')(context, data_dict)
            except NotFound:
                h.redirect_to(controller='subscription', action='index')
            except NotAuthorized:
                abort(401, _('Not authorized to see this page'))


    def create(self, id=None):
        parameters = request.params.dict_of_lists()
     
        name = request.params['subscription_name']
        type_ = request.params['subscription_type']
        
        definition = {}
        definition['type'] = type_

        if type_ == 'search':
            definition['query'] = parameters.get('query', [''])[0]
            definition['filters'] = dict([(parameter_name, parameter_list) for (parameter_name, parameter_list) in parameters.iteritems() if parameter_name in g.facets])
        else:
            for plugin in PluginImplementations(ISubscription):
                if plugin.is_responsible(definition):
                    definition = plugin.prepare_creation(definition, parameters)
                    break
            
        context = {'model': model, 'session': model.Session, 'user': c.user}
        data_dict = {'subscription_name': name, 'subscription_definition': definition}

        subscription = get_action('subscription_create')(context, data_dict)

        return h.redirect_to(controller='subscription', action='show', subscription_name=subscription['name'])


    def show(self, id=None, subscription_name=None):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True}
        data_dict = {'id': id, 'user_obj': c.userobj, 'subscription_name': subscription_name}

        self._setup_template_variables(context, data_dict)
        
        if not c.subscription:
            return render('subscription/index.html')

        type_ = c.subscription['definition']['type']

        url = None
        if type_ == 'search':
            url = h.url_for(controller='package', action='search')
            url += '?q=' + urllib.quote_plus(c.subscription['definition']['query'])

            for filter_name, filter_value_list in c.subscription['definition']['filters'].iteritems():
                for filter_value in filter_value_list:
                    url += '&%s=%s' % (filter_name, urllib.quote_plus(filter_value))
        else:
            for plugin in PluginImplementations(ISubscription):
                if plugin.is_responsible(c.subscription['definition']):
                    url = plugin.get_show_url(c.subscription)
                    break

        if not url:
            return h.redirect_to(controller='subscription', action='index')

        return h.redirect_to(str(url))


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


    def check_name(self, subscription_name):
        context = {'model': model,
                   'session': model.Session,
                   'user': c.user or c.author}
        try:
            get_action('subscription_check_name')(context, {'subscription_name': subscription_name})
        except ParameterError as e:
            return 'This name is already taken by you.'
        except NotAuthorized as e:
            return 'That\'s not you.'
            
        return ''

