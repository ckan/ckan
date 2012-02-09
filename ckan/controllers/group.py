import logging
import genshi
import datetime
from urllib import urlencode

from sqlalchemy.orm import eagerload_all
from ckan.lib.base import BaseController, c, model, request, render, h, g
from ckan.lib.base import ValidationException, abort, gettext
from pylons.i18n import get_lang, _
import ckan.authz as authz
from ckan.authz import Authorizer
from ckan.lib.helpers import Page
from ckan.plugins import PluginImplementations, IGroupController, IGroupForm
from ckan.lib.navl.dictization_functions import DataError, unflatten, validate
from ckan.logic import NotFound, NotAuthorized, ValidationError
from ckan.logic import check_access, get_action
from ckan.logic.schema import group_form_schema
from ckan.logic import tuplize_dict, clean_dict, parse_params
from ckan.lib.dictization.model_dictize import package_dictize
import ckan.forms
import ckan.logic.action.get

log = logging.getLogger(__name__)

# Mapping from group-type strings to IDatasetForm instances
_controller_behaviour_for = dict()

# The fallback behaviour
_default_controller_behaviour = None

def register_pluggable_behaviour(map):
    """
    Register the various IGroupForm instances.

    This method will setup the mappings between package types and the registered
    IGroupForm instances.  If it's called more than once an
    exception will be raised.
    """
    global _default_controller_behaviour
    
    # Create the mappings and register the fallback behaviour if one is found.
    for plugin in PluginImplementations(IGroupForm):
        if plugin.is_fallback():
            if _default_controller_behaviour is not None:
                raise ValueError, "More than one fallback "\
                                  "IGroupForm has been registered"
            _default_controller_behaviour = plugin

        for group_type in plugin.group_types():
            # Create the routes based on group_type here, this will allow us to have top level
            # objects that are actually Groups, but first we need to make sure we are not 
            # clobbering an existing domain
            
            # Our version of routes doesn't allow the environ to be passed into the match call
            # and so we have to set it on the map instead.  This looks like a threading problem
            # waiting to happen but it is executed sequentially from instead the routing setup
            e = map.environ
            map.environ = {'REQUEST_METHOD': 'GET'}
            match = map.match('/%s/new' % (group_type,))
            map.environ = e
            if match:
                raise Exception, "Plugin %r would overwrite existing urls" % plugin
            
            map.connect('%s_new' % (group_type,), 
                        '/%s/new' % (group_type,), controller='group', action='new')                
            map.connect('%s_read' % (group_type,), 
                        '/%s/{id}' %  (group_type,), controller='group', action='read')                        
            map.connect('%s_action' % (group_type,),
                        '/%s/{action}/{id}' % (group_type,), controller='group',
                requirements=dict(action='|'.join(['edit', 'authz', 'history' ]))
            )            
            
            if group_type in _controller_behaviour_for:
                raise ValueError, "An existing IGroupForm is "\
                                  "already associated with the package type "\
                                  "'%s'" % group_type
            _controller_behaviour_for[group_type] = plugin

    # Setup the fallback behaviour if one hasn't been defined.
    if _default_controller_behaviour is None:
        _default_controller_behaviour = DefaultGroupForm()


def _lookup_plugin(group_type):
    """
    Returns the plugin controller associoated with the given group type.

    If the group type is None or cannot be found in the mapping, then the
    fallback behaviour is used.
    """
    if group_type is None:
        return _default_controller_behaviour
    return _controller_behaviour_for.get(group_type,
                                         _default_controller_behaviour)


class DefaultGroupForm(object):
    """
    Provides a default implementation of the pluggable Group controller behaviour.

    This class has 2 purposes:

     - it provides a base class for IGroupForm implementations
       to use if only a subset of the method hooks need to be customised.

     - it provides the fallback behaviour if no plugin is setup to provide
       the fallback behaviour.

    Note - this isn't a plugin implementation.  This is deliberate, as
           we don't want this being registered.
    """
    
    def group_form(self):        
        return 'group/new_group_form.html'

    def form_to_db_schema(self):
        return group_form_schema()

    def db_to_form_schema(self):
        '''This is an interface to manipulate data from the database
        into a format suitable for the form (optional)'''


    def check_data_dict(self, data_dict):
        '''Check if the return data is correct, mostly for checking out if
        spammers are submitting only part of the form

        # Resources might not exist yet (eg. Add Dataset)
        surplus_keys_schema = ['__extras', '__junk', 'state', 'groups',
                               'extras_validation', 'save', 'return_to',
                               'resources']

        schema_keys = package_form_schema().keys()
        keys_in_schema = set(schema_keys) - set(surplus_keys_schema)

        missing_keys = keys_in_schema - set(data_dict.keys())

        if missing_keys:
            #print data_dict
            #print missing_keys
            log.info('incorrect form fields posted')
            raise DataError(data_dict)
        '''
        pass

    def setup_template_variables(self, context, data_dict):
        c.is_sysadmin = Authorizer().is_sysadmin(c.user)

        ## This is messy as auths take domain object not data_dict
        context_group = context.get('group',None)
        group = context_group or c.group
        if group:
            try:
                if not context_group:
                    context['group'] = group
                check_access('group_change_state',context)
                c.auth_for_change_state = True
            except NotAuthorized:
                c.auth_for_change_state = False

##############      End of pluggable group behaviour     ############## 


class GroupController(BaseController):

    ## hooks for subclasses 

    def _group_form(self, group_type=None):
        return _lookup_plugin(group_type).group_form()
        
    def _form_to_db_schema(self, group_type=None):
        return _lookup_plugin(group_type).form_to_db_schema()

    def _db_to_form_schema(self, group_type=None):
        '''This is an interface to manipulate data from the database
        into a format suitable for the form (optional)'''
        return _lookup_plugin(group_type).form_to_db_schema()

    def _setup_template_variables(self, context, data_dict, group_type=None):
        return _lookup_plugin(group_type).setup_template_variables(context,data_dict)

    ## end hooks

    def index(self):

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author}

        data_dict = {'all_fields': True}

        try:
            check_access('site_read', context)
        except NotAuthorized:
            abort(401, _('Not authorized to see this page'))
        
        results = get_action('group_list')(context, data_dict)

        c.page = Page(
            collection=results,
            page=request.params.get('page', 1),
            url=h.pager_url,
            items_per_page=20
        )
        return render('group/index.html')


    def read(self, id):
        from ckan.lib.search import SearchError
        group_type = self._get_group_type(id.split('@')[0])        
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'schema': self._form_to_db_schema(group_type=type)}
        data_dict = {'id': id}
        q = c.q = request.params.get('q', '') # unicode format (decoded from utf8)

        try:
            c.group_dict = get_action('group_show')(context, data_dict)
            c.group = context['group']
        except NotFound:
            abort(404, _('Group not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read group %s') % id)

        # Search within group
        q += ' groups: "%s"' % c.group_dict.get('name')

        try:
            description_formatted = ckan.misc.MarkdownFormat().to_html(c.group_dict.get('description',''))
            c.description_formatted = genshi.HTML(description_formatted)
        except Exception, e:
            error_msg = "<span class='inline-warning'>%s</span>" % _("Cannot render description")
            c.description_formatted = genshi.HTML(error_msg)
        
        c.group_admins = self.authorizer.get_admins(c.group)

        context['return_query'] = True

        limit = 20
        try:
            page = int(request.params.get('page', 1))
        except ValueError, e:
            abort(400, ('"page" parameter must be an integer'))
            
        # most search operations should reset the page counter:
        params_nopage = [(k, v) for k,v in request.params.items() if k != 'page']

        def search_url(params):
            url = h.url_for(controller='group', action='read', id=c.group_dict.get('name'))
            params = [(k, v.encode('utf-8') if isinstance(v, basestring) else str(v)) \
                            for k, v in params]
            return url + u'?' + urlencode(params)

        def drill_down_url(**by):
            params = list(params_nopage)
            params.extend(by.items())
            return search_url(set(params))
        
        c.drill_down_url = drill_down_url 
        
        def remove_field(key, value):
            params = list(params_nopage)
            params.remove((key, value))
            return search_url(params)

        c.remove_field = remove_field

        def pager_url(q=None, page=None):
            params = list(params_nopage)
            params.append(('page', page))
            return search_url(params)

        try:
            c.fields = []
            search_extras = {}
            for (param, value) in request.params.items():
                if not param in ['q', 'page'] \
                        and len(value) and not param.startswith('_'):
                    if not param.startswith('ext_'):
                        c.fields.append((param, value))
                        q += ' %s: "%s"' % (param, value)
                    else:
                        search_extras[param] = value

            data_dict = {
                'q':q,
                'facet.field':g.facets,
                'rows':limit,
                'start':(page-1)*limit,
                'extras':search_extras
            }

            query = get_action('package_search')(context,data_dict)

            c.page = h.Page(
                collection=query['results'],
                page=page,
                url=pager_url,
                item_count=query['count'],
                items_per_page=limit
            )
            c.facets = query['facets']
            c.page.items = query['results']
        except SearchError, se:
            log.error('Group search error: %r', se.args)
            c.query_error = True
            c.facets = {}
            c.page = h.Page(collection=[])

        # Add the group's activity stream (already rendered to HTML) to the
        # template context for the group/read.html template to retrieve later.
        c.group_activity_stream = \
                ckan.logic.action.get.group_activity_list_html(context,
                    {'id': c.group_dict['id']})
        
        return render('group/read.html')

    def new(self, data=None, errors=None, error_summary=None):
        
        group_type = request.path.strip('/').split('/')[0]
        if group_type == 'group':
            group_type = None
            if data:
                data['type'] = group_type
        
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'extras_as_string': True,
                   'schema': self._form_to_db_schema(),
                   'save': 'save' in request.params }
        try:
            check_access('group_create',context)
        except NotAuthorized:
            abort(401, _('Unauthorized to create a group'))

        if context['save'] and not data:
            return self._save_new(context, group_type)
        
        data = data or {}
        errors = errors or {}
        error_summary = error_summary or {}
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary}

        self._setup_template_variables(context,data)
        c.form = render(self._group_form(group_type=group_type), extra_vars=vars)
        return render('group/new.html')

    def edit(self, id, data=None, errors=None, error_summary=None):
        group_type = self._get_group_type(id.split('@')[0])                
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'extras_as_string': True,
                   'save': 'save' in request.params,
                   'schema': self._form_to_db_schema(group_type=group_type),
                   }
        data_dict = {'id': id}

        if context['save'] and not data:
            return self._save_edit(id, context)

        try:
            old_data = get_action('group_show')(context, data_dict)
            c.grouptitle = old_data.get('title')
            c.groupname = old_data.get('name')
            schema = self._db_to_form_schema()
            if schema and not data:
                old_data, errors = validate(old_data, schema, context=context)

            data = data or old_data
        except NotFound:
            abort(404, _('Group not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read group %s') % '')

        group = context.get("group")
        c.group = group


        try:
            check_access('group_update',context)
        except NotAuthorized, e:
            abort(401, _('User %r not authorized to edit %s') % (c.user, id))

        errors = errors or {}
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary}

        self._setup_template_variables(context, data, group_type=group_type)
        c.form = render(self._group_form(group_type), extra_vars=vars)
        return render('group/edit.html')

    def _get_group_type(self, id):
        """
        Given the id of a group it determines the plugin to load 
        based on the group's type name (type). The plugin found
        will be returned, or None if there is no plugin associated with 
        the type.

        Uses a minimal context to do so.  The main use of this method
        is for figuring out which plugin to delegate to.

        aborts if an exception is raised.
        """
        global _controller_behaviour_for
        
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author}
        try:
            data = get_action('group_show')(context, {'id': id})
        except NotFound:
            abort(404, _('Group not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read group %s') % id)
        return data['type']


    def _save_new(self, context, group_type=None):
        try:
            data_dict = clean_dict(unflatten(
                tuplize_dict(parse_params(request.params))))
            data_dict['type'] = group_type or 'group'
            context['message'] = data_dict.get('log_message', '')
            group = get_action('group_create')(context, data_dict)
            
            # Redirect to the appropriate _read route for the type of group
            h.redirect_to( group['type'] + '_read', id=group['name'])
        except NotAuthorized:
            abort(401, _('Unauthorized to read group %s') % '')
        except NotFound, e:
            abort(404, _('Group not found'))
        except DataError:
            abort(400, _(u'Integrity Error'))
        except ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.new(data_dict, errors, error_summary)

    def _save_edit(self, id, context):
        try:
            data_dict = clean_dict(unflatten(
                tuplize_dict(parse_params(request.params))))
            context['message'] = data_dict.get('log_message', '')
            data_dict['id'] = id
            group = get_action('group_update')(context, data_dict)
            h.redirect_to(controller='group', action='read', id=group['name'])
        except NotAuthorized:
            abort(401, _('Unauthorized to read group %s') % id)
        except NotFound, e:
            abort(404, _('Group not found'))
        except DataError:
            abort(400, _(u'Integrity Error'))
        except ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.edit(id, data_dict, errors, error_summary)

    def authz(self, id):
        group = model.Group.get(id)
        if group is None:
            abort(404, _('Group not found'))
        c.groupname = group.name
        c.grouptitle = group.display_name

        try:
            context = {'model':model,'user':c.user or c.author, 'group':group}
            check_access('group_edit_permissions',context)
            c.authz_editable = True
            c.group = context['group']
        except NotAuthorized:
            c.authz_editable = False
        if not c.authz_editable:
            abort(401, gettext('User %r not authorized to edit %s authorizations') % (c.user, id))

        roles = self._handle_update_of_authz(group)
        self._prepare_authz_info_for_render(roles)
        return render('group/authz.html')


    def history(self, id):
        if 'diff' in request.params or 'selected1' in request.params:
            try:
                params = {'id':request.params.getone('group_name'),
                          'diff':request.params.getone('selected1'),
                          'oldid':request.params.getone('selected2'),
                          }
            except KeyError, e:
                if dict(request.params).has_key('group_name'):
                    id = request.params.getone('group_name')
                c.error = _('Select two revisions before doing the comparison.')
            else:
                params['diff_entity'] = 'group'
                h.redirect_to(controller='revision', action='diff', **params)

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'schema': self._form_to_db_schema()}
        data_dict = {'id': id}
        try:
            c.group_dict = get_action('group_show')(context, data_dict)
            c.group_revisions = get_action('group_revision_list')(context, data_dict)
            #TODO: remove
            # Still necessary for the authz check in group/layout.html
            c.group = context['group']
        except NotFound:
            abort(404, _('Group not found'))
        except NotAuthorized:
            abort(401, _('User %r not authorized to edit %r') % (c.user, id))

        format = request.params.get('format', '')
        if format == 'atom':
            # Generate and return Atom 1.0 document.
            from webhelpers.feedgenerator import Atom1Feed
            feed = Atom1Feed(
                title=_(u'CKAN Group Revision History'),
                link=h.url_for(controller='group', action='read', id=c.group_dict['name']),
                description=_(u'Recent changes to CKAN Group: ') +
                    c.group_dict['display_name'],
                language=unicode(get_lang()),
            )
            for revision_dict in c.group_revisions:
                revision_date = h.date_str_to_datetime(revision_dict['timestamp'])
                try:
                    dayHorizon = int(request.params.get('days'))
                except:
                    dayHorizon = 30
                dayAge = (datetime.datetime.now() - revision_date).days
                if dayAge >= dayHorizon:
                    break
                if revision_dict['message']:
                    item_title = u'%s' % revision_dict['message'].split('\n')[0]
                else:
                    item_title = u'%s' % revision_dict['id']
                item_link = h.url_for(controller='revision', action='read', id=revision_dict['id'])
                item_description = _('Log message: ')
                item_description += '%s' % (revision_dict['message'] or '')
                item_author_name = revision_dict['author']
                item_pubdate = revision_date
                feed.add_item(
                    title=item_title,
                    link=item_link,
                    description=item_description,
                    author_name=item_author_name,
                    pubdate=item_pubdate,
                )
            feed.content_type = 'application/atom+xml'
            return feed.writeString('utf-8')
        return render('group/history.html')

    def _render_edit_form(self, fs):
        # errors arrive in c.error and fs.errors
        c.fieldset = fs
        c.fieldset2 = ckan.forms.get_package_group_fieldset()
        return render('group/edit_form.html')

    def _update(self, fs, group_name, group_id):
        '''
        Writes the POST data (associated with a group edit) to the database
        @input c.error
        '''
        validation = fs.validate()
        if not validation:
            c.form = self._render_edit_form(fs)
            raise ValidationException(fs)

        try:
            fs.sync()
        except Exception, inst:
            model.Session.rollback()
            raise
        else:
            model.Session.commit()

    def _update_authz(self, fs):
        validation = fs.validate()
        if not validation:
            c.form = self._render_edit_form(fs)
            raise ValidationException(fs)
        try:
            fs.sync()
        except Exception, inst:
            model.Session.rollback()
            raise
        else:
            model.Session.commit()
