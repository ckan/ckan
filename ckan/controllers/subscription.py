import json
import logging
import genshi
import ckan.lib.helpers as h
import ckan.misc
import ckan.model as model
import ckan.lib.i18n
import ckan.lib.base as base
import ckan.logic as logic
import ckan.plugins as p


log = logging.getLogger(__name__)


class SubscriptionController(base.BaseController):

    def __before__(self, action, **env):
        base.BaseController.__before__(self, action, **env)
        try:
            context = {'model': model, 'user': base.c.user or base.c.author}
            logic.check_access('site_read', context)
        except logic.NotAuthorized:
            if base.c.action not in ('login', 'request_reset', 'perform_reset',):
                abort(401, _('Not authorized to see this page'))


    def _setup_template_variables(self, context, data_dict):
        base.c.is_sysadmin = Authorizer().is_sysadmin(base.c.user)
        try:
            user_dict = logic.get_action('user_show')(context, data_dict)
        except logic.NotFound:
            h.redirect_to(controller='user', action='login', id=None)
        except logic.NotAuthorized:
            abort(401, _('Not authorized to see this page'))
        data_dict['id'] = user_dict['id']
        base.c.user_dict = user_dict
        base.c.is_myself = user_dict['name'] == base.c.user

        try:
            base.c.subscriptions = logic.get_action('subscription_list')(context, data_dict)
        except logic.NotFound:
            h.redirect_to(controller='subscription', action='index')
        except logic.NotAuthorized:
            abort(401, _('Not authorized to see this page'))

        if data_dict.has_key('subscription_name'):
            try:
                base.c.subscription = logic.get_action('subscription_show')(context, data_dict)
            except logic.NotFound:
                h.redirect_to(controller='subscription', action='index')
            except logic.NotAuthorized:
                abort(401, _('Not authorized to see this page'))


    def create(self, id=None):
        parameters = base.request.params.dict_of_lists()
     
        name = base.request.params['subscription_name']
        type_ = base.request.params['subscription_type']
        
        definition = {}
        definition['type'] = type_

        if type_ == 'search':
            definition['query'] = parameters.get('query', [''])[0]
            definition['filters'] = dict([(parameter_name, parameter_list) for (parameter_name, parameter_list) in parameters.iteritems() if parameter_name in base.g.facets])
        else:
            for plugin in p.PluginImplementations(p.ISubscription):
                if plugin.is_responsible(definition):
                    definition = plugin.prepare_creation(definition, parameters)
                    break
            
        context = {'model': model, 'session': model.Session, 'user': base.c.user}
        data_dict = {'subscription_name': name, 'subscription_definition': definition}

        subscription = logic.get_action('subscription_create')(context, data_dict)

        return h.redirect_to(controller='subscription', action='show', subscription_name=subscription['name'])


    def show(self, id=None, subscription_name=None):
        context = {'model': model, 'session': model.Session,
                   'user': base.c.user or base.c.author, 'for_view': True}
        data_dict = {'id': id, 'user_obj': base.c.userobj, 'subscription_name': subscription_name}

        self._setup_template_variables(context, data_dict)
        
        if not base.c.subscription:
            return render('subscription/index.html')

        type_ = base.c.subscription['definition']['type']

        url = None
        if type_ == 'search':
            url = h.url_for(controller='package', action='search')
            url += '?q=' + urllib.quote_plus(base.c.subscription['definition']['query'])

            for filter_name, filter_value_list in base.c.subscription['definition']['filters'].iteritems():
                for filter_value in filter_value_list:
                    url += '&%s=%s' % (filter_name, urllib.quote_plus(filter_value))
        else:
            for plugin in p.PluginImplementations(p.ISubscription):
                if plugin.is_responsible(base.c.subscription['definition']):
                    url = plugin.get_show_url(base.c.subscription)
                    break

        if not url:
            return h.redirect_to(controller='subscription', action='index')

        return h.redirect_to(str(url))


    def mark_changes_as_seen(self, subscription_name=None):
        context = {'model': model, 'session': model.Session,
                   'user': base.c.user or base.c.author, 'for_view': True}
        data_dict = {'subscription_name': subscription_name}

        logic.get_action('subscription_mark_changes_as_seen')(context, data_dict)

        return h.redirect_to(controller='subscription', action='show', subscription_name=subscription_name)
        
        
    def delete(self, subscription_name):
        context = {'model': model, 'session': model.Session,
                   'user': base.c.user or base.c.author, 'for_view': True}
        data_dict = {'subscription_name': subscription_name}

        logic.get_action('subscription_delete')(context, data_dict)

        return redirect(base.request.params['return_url'])
