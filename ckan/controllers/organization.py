import logging
import genshi
import datetime
from urllib import urlencode

from ckan.lib.base import (BaseController, c, model, request, render, h, g)
import ckan.lib.dictization.model_save as model_save

from ckan.lib.base import abort
import pylons.config as config
from pylons.i18n import get_lang, _
from ckan.lib.helpers import Page
import ckan.lib.maintain as maintain
from ckan.lib.navl.dictization_functions import (DataError, unflatten)
from ckan.logic import NotFound, NotAuthorized, ValidationError
from ckan.logic import check_access, get_action
from ckan.logic import tuplize_dict, clean_dict, parse_params
import ckan.logic.schema as schema
import ckan.authz as authz
import ckan.forms
import ckan.logic as logic
import ckan.logic.action.get
import ckan.logic.action as action
import ckan.lib.search as search
import ckan.lib.mailer as mailer


log = logging.getLogger(__name__)


class OrganizationController(BaseController):
    """
    An Organization is modelled in the same way as a group, it is
    implemented using the Group model and uses the type field to
    differentiate itself from normal 'Groups'.  We provide a different
    controller and templates to make it easy to differentiate between the
    two and so they can diverge.
    """

    def form_to_db_schema(self):
        return schema.organization_form_schema()

    def db_to_form_schema(self):
        '''This is an interface to manipulate data from the database
        into a format suitable for the form (optional)'''

    def index(self):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True,
                   'with_private': False}

        data_dict = {'all_fields': True}

        try:
            check_access('site_read', context)
        except NotAuthorized:
            abort(401, _('Not authorized to see this page'))

        results = get_action('organization_list')(context, data_dict)

        c.page = Page(
            collection=results,
            page=request.params.get('page', 1),
            url=h.pager_url,
            items_per_page=20
        )
        return render('organization/index.html')

    def read(self, id):
        from ckan.lib.search import SearchError
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'schema': self.db_to_form_schema(),
                   'for_view': True, 'extras_as_string': True}
        data_dict = {'id': id}
        # unicode format (decoded from utf8)
        q = c.q = request.params.get('q', '')

        try:
            c.organization_dict = get_action('organization_show')(context, data_dict)
            c.organization = context['organization']
        except NotFound:
            abort(404, _('Organization not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read organization %s') % id)

        # Search within group
        q += ' organizations: "%s"' % c.organization_dict.get('name')

        try:
            description_formatted = ckan.misc.MarkdownFormat().to_html(
            c.organization_dict.get('description', ''))
            c.description_formatted = genshi.HTML(description_formatted)
        except Exception:
            error_msg = "<span class='inline-warning'>%s</span>" %\
                        _("Cannot render description")
            c.description_formatted = genshi.HTML(error_msg)


        c.organization_admins = c.organization.members_of_type(model.User, 'admin').all()
        c.organization_members = c.organization.members_of_type(model.User, 'editor').all()

        context['return_query'] = True

        limit = 20
        try:
            page = int(request.params.get('page', 1))
        except ValueError:
            abort(400, ('"page" parameter must be an integer'))

        # most search operations should reset the page counter:
        params_nopage = [(k, v) for k, v in request.params.items()
                         if k != 'page']
        sort_by = request.params.get('sort', None)

        def search_url(params):
            url = h.url_for(controller='organization', action='read',
                            id=c.organization_dict.get('name'))
            params = [(k, v.encode('utf-8') if isinstance(v, basestring)
                       else str(v)) for k, v in params]
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
                if not param in ['q', 'page', 'sort'] \
                        and len(value) and not param.startswith('_'):
                    if not param.startswith('ext_'):
                        c.fields.append((param, value))
                        q += ' %s: "%s"' % (param, value)
                    else:
                        search_extras[param] = value

            fq = 'capacity:"public"'
            if (c.userobj and c.organization and c.userobj.is_in_group(c.organization)):
                fq = ''
                context['ignore_capacity_check'] = True

            data_dict = {
                'q': q,
                'fq': fq,
                'facet.field': g.facets,
                'rows': limit,
                'sort': sort_by,
                'start': (page - 1) * limit,
                'extras': search_extras
            }

            query = get_action('package_search')(context, data_dict)

            c.page = h.Page(
                collection=query['results'],
                page=page,
                url=pager_url,
                item_count=query['count'],
                items_per_page=limit
            )

            c.facets = query['facets']
            maintain.deprecate_context_item(
              'facets',
              'Use `c.search_facets` instead.')

            c.search_facets = query['search_facets']
            c.page.items = query['results']

            c.sort_by_selected = sort_by

        except SearchError, se:
            log.error('Organization search error: %r', se.args)
            c.query_error = True
            c.facets = {}
            c.page = h.Page(collection=[])

        # Add the organizations's activity stream (already rendered to HTML)
        # to the template context for the orgzniation/read.html template to retrieve
        # later.
        c.organization_activity_stream = \
            get_action('organization_activity_list_html')(context,
                                                   {'id': c.organization_dict['id']})

        return render('organization/read.html')

    def new(self, data=None, errors=None, error_summary=None):
        if data:
            data['type'] = 'organization'

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'extras_as_string': True,
                   'save': 'save' in request.params,
                   'parent': request.params.get('parent', None)}
        try:
            check_access('organization_create', context)
        except NotAuthorized:
            abort(401, _('Unauthorized to create an organization'))

        if context['save'] and not data:
            return self._save_new(context)

        data = data or {}
        errors = errors or {}
        error_summary = error_summary or {}
        vars = {'data': data, 'errors': errors,
                'error_summary': error_summary,
                'action': 'new'}

        self.setup_template_variables(context, data)
        c.form = render('organization/form.html',
                        extra_vars=vars)
        return render('organization/new.html')

    def edit(self, id, data=None, errors=None, error_summary=None):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'extras_as_string': True,
                   'save': 'save' in request.params,
                   'for_edit': True,
                   'parent': request.params.get('parent', None)
                   }
        data_dict = {'id': id}

        if context['save'] and not data:
            return self._save_edit(id, context)

        try:
            old_data = get_action('organization_show')(context, data_dict)
            c.organizationtitle = old_data.get('title')
            c.organizationname = old_data.get('name')
            data = data or old_data
        except NotFound:
            abort(404, _('Organization not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read organization %s') % '')

        organization = context.get("organization")
        c.organization = organization

        try:
            check_access('organization_update', context)
        except NotAuthorized:
            abort(401, _('User %r not authorized to edit %s') % (c.user, id))

        errors = errors or {}
        vars = {'data': data, 'errors': errors,
                'error_summary': error_summary,
                'action': 'edit'}

        self.setup_template_variables(context, data)
        c.form = render('organization/form.html', extra_vars=vars)
        return render('organization/edit.html')


    def _save_new(self, context):
        try:
            data_dict = clean_dict(unflatten(
                tuplize_dict(parse_params(request.params))))
            data_dict['type'] = 'organization'
            context['message'] = data_dict.get('log_message', '')
            data_dict['users'] = [{'name': c.user, 'capacity': 'admin'}]
            organization = get_action('organization_create')(context, data_dict)

            # Redirect to the appropriate _read route for the type of group
            h.redirect_to('organization_read', id=organization['name'])
        except NotAuthorized:
            abort(401, _('Unauthorized to read organization %s') % '')
        except NotFound, e:
            abort(404, _('Organization not found'))
        except DataError:
            abort(400, _(u'Integrity Error'))
        except ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.new(data_dict, errors, error_summary)

    def _force_reindex(self, grp):
        ''' When the organization name has changed, we need to force a reindex
        of the datasets within the organization, otherwise they will stop
        appearing on the read page for the organization (as they're connected via
        the organization name)'''
        organization = model.Group.get(grp['name'])
        for dataset in organization.active_packages().all():
            search.rebuild(dataset.name)

    def _save_edit(self, id, context):
        try:
            data_dict = clean_dict(unflatten(
                tuplize_dict(parse_params(request.params))))
            context['message'] = data_dict.get('log_message', '')
            data_dict['id'] = id
            context['allow_partial_update'] = True
            organization = get_action('organization_update')(context, data_dict)

            if id != organization['name']:
                self._force_reindex(organization)

            h.redirect_to('organization_read', id=organization['name'])
        except NotAuthorized:
            abort(401, _('Unauthorized to read organization %s') % id)
        except NotFound, e:
            abort(404, _('Organization not found'))
        except DataError:
            abort(400, _(u'Integrity Error'))
        except ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.edit(id, data_dict, errors, error_summary)

    def history(self, id):
        if 'diff' in request.params or 'selected1' in request.params:
            try:
                params = {'id': request.params.getone('group_name'),
                          'diff': request.params.getone('selected1'),
                          'oldid': request.params.getone('selected2'),
                          }
            except KeyError:
                if 'group_name' in dict(request.params):
                    id = request.params.getone('group_name')
                c.error = \
                    _('Select two revisions before doing the comparison.')
            else:
                params['diff_entity'] = 'group'
                h.redirect_to(controller='revision', action='diff', **params)

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'schema': self.form_to_db_schema()}
        data_dict = {'id': id}
        try:
            c.organization_dict = get_action('organization_show')(context, data_dict)
            c.organization_revisions = get_action('organization_revision_list')(context,
                                                                  data_dict)
            c.organization = context['organization']
        except NotFound:
            abort(404, _('Organization not found'))
        except NotAuthorized:
            abort(401, _('User %r not authorized to edit %r') % (c.user, id))

        format = request.params.get('format', '')
        if format == 'atom':
            # Generate and return Atom 1.0 document.
            from webhelpers.feedgenerator import Atom1Feed
            feed = Atom1Feed(
                title=_(u'CKAN Organization Revision History'),
                link=h.url_for(controller='organization', action='read',
                               id=c.organization_dict['name']),
                description=_(u'Recent changes to CKAN Organization: ') +
                c.organization_dict['display_name'],
                language=unicode(get_lang()),
            )
            for revision_dict in c.organization_revisions:
                revision_date = h.date_str_to_datetime(
                    revision_dict['timestamp'])
                try:
                    dayHorizon = int(request.params.get('days'))
                except:
                    dayHorizon = 30
                dayAge = (datetime.datetime.now() - revision_date).days
                if dayAge >= dayHorizon:
                    break
                if revision_dict['message']:
                    item_title = u'%s' % revision_dict['message'].\
                        split('\n')[0]
                else:
                    item_title = u'%s' % revision_dict['id']
                item_link = h.url_for(controller='revision', action='read',
                                      id=revision_dict['id'])
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
        return render('organization/history.html')


    def _send_application(self, organization, reason):
        from genshi.template.text import NewTextTemplate

        if not reason:
            h.flash_error(_("There was a problem with your submission, \
                             please correct it and try again"))
            errors = {"reason": ["No reason was supplied"]}
            return self.apply(organization.id, errors=errors,
                              error_summary=action.error_summary(errors))

        admins = organization.members_of_type(model.User, 'admin').all()
        recipients = [(u.fullname, u.email) for u in admins] if admins else \
                     [(config.get('ckan.admin.name', "CKAN Administrator"),
                       config.get('ckan.admin.email', None), )]

        if not recipients:
            h.flash_error(
                _("There is a problem with the system configuration"))
            errors = {"reason": ["No organization administrator exists"]}
            return self.apply(organization.id, data=None, errors=errors,
                              error_summary=action.error_summary(errors))

        extra_vars = {
            'organization': organization,
            'requester': c.userobj,
            'reason': reason
        }
        email_msg = render("organization/email/join_publisher_request.txt",
                           extra_vars=extra_vars,
                           loader_class=NewTextTemplate)

        try:
            for (name, recipient) in recipients:
                mailer.mail_recipient(name,
                               recipient,
                               "Organization request",
                               email_msg)
        except:
            h.flash_error(
                _("There is a problem with the system configuration"))
            errors = {"reason": ["No mail server was found"]}
            return self.apply(organization.id, errors=errors,
                              error_summary=action.error_summary(errors))

        h.flash_success(_("Your application has been submitted"))
        h.redirect_to('organization_read', id=organization.name)

    def apply(self, id=None, data=None, errors=None, error_summary=None):
        """
        A user has requested access to this publisher and so we will send an
        email to any admins within the publisher.
        """
        if not c.user:
            abort(401, _('You must be logged in to apply for membership'))

        if 'parent' in request.params and not id:
            id = request.params['parent']

        if id:
            c.organization = model.Group.get(id)
            if 'save' in request.params and not errors:
                return self._send_application(
                    c.organization, request.params.get('reason', None))

        self._add_organization_list()
        data = data or {}
        errors = errors or {}
        error_summary = error_summary or {}

        data.update(request.params)

        vars = {'data': data, 'errors': errors, 'error_summary': error_summary}
        c.form = render('organization/apply_form.html', extra_vars=vars)
        return render('organization/apply.html')

    def _add_users(self, group, parameters):
        if not group:
            h.flash_error(_("There was a problem with your submission, \
                             please correct it and try again"))
            errors = {"reason": ["No reason was supplied"]}
            return self.apply(group.id, errors=errors,
                              error_summary=action.error_summary(errors))

        data_dict = logic.clean_dict(unflatten(
                logic.tuplize_dict(logic.parse_params(request.params))))
        data_dict['id'] = group.id

        # Temporary fix for strange caching during dev
        l = data_dict['users']
        for d in l:
            d['capacity'] = d.get('capacity', 'editor')

        context = {
            "group": group,
            "schema": schema.default_organization_schema(),
            "model": model,
            "session": model.Session
        }

        # Temporary cleanup of a capacity being sent without a name
        users = [d for d in data_dict['users'] if len(d) == 2]
        data_dict['users'] = users

        model.repo.new_revision()
        model_save.group_member_save(context, data_dict, 'users')
        model.Session.commit()

        h.redirect_to(controller='organization', action='users', id=group.name)

    def users(self, id, data=None, errors=None, error_summary=None):
        c.organization = model.Group.get(id)

        if not c.organization:
            abort(404, _('Group not found'))

        context = {
                   'model': model,
                   'session': model.Session,
                   'user': c.user or c.author,
                   'organization': c.organization}

        try:
            logic.check_access('organization_update', context)
        except logic.NotAuthorized:
            abort(401, _('User %r not authorized to edit %s') % (c.user, id))

        if 'save' in request.params and not errors:
            return self._add_users(c.organization, request.params)

        data = data or {}
        errors = errors or {}
        error_summary = error_summary or {}

        data['users'] = []
        data['users'].extend({"name": user.name,
                              "capacity": "admin"}
                              for user in c.organization.members_of_type(
                                model.User, "admin").all())
        data['users'].extend({"name": user.name,
                              "capacity": "editor"}
                              for user in c.organization.members_of_type(
                                model.User, 'editor').all())

        vars = {'data': data, 'errors': errors, 'error_summary': error_summary}
        c.form = render('organization/users_form.html', extra_vars=vars)

        return render('organization/users.html')

    def _add_organization_list(self):
        c.possible_parents = model.Session.query(model.Group).\
               filter(model.Group.state == 'active').\
               filter(model.Group.type == 'organization').\
               order_by(model.Group.title).all()
        if c.user:
            c.possible_parents = [o for o in c.possible_parents
                                  if not o
                                  in c.userobj.get_groups('organization')]

    def setup_template_variables(self, context, data_dict):
        c.is_sysadmin = authz.Authorizer().is_sysadmin(c.user)

        context_organization = context.get('organization', None)
        organization = context_organization or c.organization
        if organization:
            try:
                if not context_organization:
                    context['organization'] = organization
                logic.check_access('organization_change_state', context)
                c.auth_for_change_state = True
            except logic.NotAuthorized:
                c.auth_for_change_state = False
