import logging
from urllib import urlencode
import datetime

from pylons import config
from pylons.i18n import _
from autoneg.accept import negotiate

from ckan.logic import get_action, check_access
from ckan.lib.helpers import date_str_to_datetime
from ckan.lib.base import request, c, BaseController, model, abort, h, g, render
from ckan.lib.base import response, redirect, gettext
from ckan.lib.package_saver import PackageSaver, ValidationException
from ckan.lib.navl.dictization_functions import DataError, unflatten, validate
from ckan.lib.helpers import json
from ckan.logic import NotFound, NotAuthorized, ValidationError
from ckan.logic import tuplize_dict, clean_dict, parse_params, flatten_to_string_key
from ckan.lib.i18n import get_lang
import ckan.forms
import ckan.authz
import ckan.rating
import ckan.misc
import ckan.logic.action.get
from home import CACHE_PARAMETER

from lib.plugins import lookup_package_plugin

log = logging.getLogger(__name__)

def search_url(params):
    url = h.url_for(controller='package', action='search')
    params = [(k, v.encode('utf-8') if isinstance(v, basestring) else str(v)) \
                    for k, v in params]
    return url + u'?' + urlencode(params)

autoneg_cfg = [
    ("application", "xhtml+xml", ["html"]),
    ("text", "html", ["html"]),
    ("application", "rdf+xml", ["rdf"]),
    ("application", "turtle", ["ttl"]),
    ("text", "plain", ["nt"]),
    ("text", "x-graphviz", ["dot"]),
    ]

class PackageController(BaseController):

    def _package_form(self, package_type=None):    
        return lookup_package_plugin(package_type).package_form()

    def _form_to_db_schema(self, package_type=None):
        return lookup_package_plugin(package_type).form_to_db_schema()

    def _db_to_form_schema(self, package_type=None):
        '''This is an interface to manipulate data from the database
        into a format suitable for the form (optional)'''
        return lookup_package_plugin(package_type).db_to_form_schema()

    def _check_data_dict(self, data_dict, package_type=None):
        '''Check if the return data is correct, mostly for checking out if
        spammers are submitting only part of the form'''
        return lookup_package_plugin(package_type).check_data_dict(data_dict)

    def _setup_template_variables(self, context, data_dict, package_type=None):
        return lookup_package_plugin(package_type).setup_template_variables(context, data_dict)

    authorizer = ckan.authz.Authorizer()

    def search(self):
        from ckan.lib.search import SearchError
        try:
            context = {'model':model,'user': c.user or c.author}
            check_access('site_read',context)
        except NotAuthorized:
            abort(401, _('Not authorized to see this page'))

        q = c.q = request.params.get('q', u'') # unicode format (decoded from utf8)
        c.query_error = False
        try:
            page = int(request.params.get('page', 1))
        except ValueError, e:
            abort(400, ('"page" parameter must be an integer'))
        limit = 20

        # most search operations should reset the page counter:
        params_nopage = [(k, v) for k,v in request.params.items() if k != 'page']
        
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
            fq = ''
            for (param, value) in request.params.items():
                if not param in ['q', 'page'] \
                        and len(value) and not param.startswith('_'):
                    if not param.startswith('ext_'):
                        c.fields.append((param, value))
                        fq += ' %s:"%s"' % (param, value)
                    else:
                        search_extras[param] = value

            context = {'model': model, 'session': model.Session,
                       'user': c.user or c.author, 'for_view': True}

            data_dict = {
                'q':q,
                'fq':fq,
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
            log.error('Dataset search error: %r', se.args)
            c.query_error = True
            c.facets = {}
            c.page = h.Page(collection=[])
        
        return render('package/search.html')


    def read(self, id):
        package_type = self._get_package_type(id.split('@')[0])
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'extras_as_string': True,
                   'for_view': True}
        data_dict = {'id': id}

        # interpret @<revision_id> or @<date> suffix
        split = id.split('@')
        if len(split) == 2:
            data_dict['id'], revision_ref = split
            if model.is_id(revision_ref):
                context['revision_id'] = revision_ref
            else:
                try:
                    date = date_str_to_datetime(revision_ref)
                    context['revision_date'] = date
                except TypeError, e:
                    abort(400, _('Invalid revision format: %r') % e.args)
                except ValueError, e:
                    abort(400, _('Invalid revision format: %r') % e.args)
        elif len(split) > 2:
            abort(400, _('Invalid revision format: %r') % 'Too many "@" symbols')
            
        #check if package exists
        try:
            c.pkg_dict = get_action('package_show')(context, data_dict)
            c.pkg = context['package']
            c.pkg_json = json.dumps(c.pkg_dict)
        except NotFound:
            abort(404, _('Dataset not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read package %s') % id)
        
        #set a cookie so we know whether to display the welcome message
        c.hide_welcome_message = bool(request.cookies.get('hide_welcome_message', False))
        response.set_cookie('hide_welcome_message', '1', max_age=3600) #(make cross-site?)

        # used by disqus plugin
        c.current_package_id = c.pkg.id

        # Add the package's activity stream (already rendered to HTML) to the
        # template context for the package/read.html template to retrieve
        # later.
        c.package_activity_stream = \
                ckan.logic.action.get.package_activity_list_html(context,
                    {'id': c.current_package_id})

        if config.get('rdf_packages'):
            accept_header = request.headers.get('Accept', '*/*')
            for content_type, exts in negotiate(autoneg_cfg, accept_header):
                if "html" not in exts: 
                    rdf_url = '%s%s.%s' % (config['rdf_packages'], c.pkg.id, exts[0])
                    redirect(rdf_url, code=303)
                break

        PackageSaver().render_package(c.pkg_dict, context)
        return render('package/read.html')

    def comments(self, id):
        package_type = self._get_package_type(id)
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'extras_as_string': True,}

        #check if package exists
        try:
            c.pkg_dict = get_action('package_show')(context, {'id':id})
            c.pkg = context['package']
        except NotFound:
            abort(404, _('Dataset not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read package %s') % id)

        # used by disqus plugin
        c.current_package_id = c.pkg.id

        #render the package
        PackageSaver().render_package(c.pkg_dict)
        return render('package/comments.html')


    def history(self, id):
        if 'diff' in request.params or 'selected1' in request.params:
            try:
                params = {'id':request.params.getone('pkg_name'),
                          'diff':request.params.getone('selected1'),
                          'oldid':request.params.getone('selected2'),
                          }
            except KeyError, e:
                if dict(request.params).has_key('pkg_name'):
                    id = request.params.getone('pkg_name')
                c.error = _('Select two revisions before doing the comparison.')
            else:
                params['diff_entity'] = 'package'
                h.redirect_to(controller='revision', action='diff', **params)

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'extras_as_string': True,}
        data_dict = {'id':id}
        try:
            c.pkg_dict = get_action('package_show')(context, data_dict)
            c.pkg_revisions = get_action('package_revision_list')(context, data_dict)
            #TODO: remove
            # Still necessary for the authz check in group/layout.html
            c.pkg = context['package']

        except NotAuthorized:
            abort(401, _('Unauthorized to read package %s') % '')
        except NotFound:
            abort(404, _('Dataset not found'))

        format = request.params.get('format', '')
        if format == 'atom':
            # Generate and return Atom 1.0 document.
            from webhelpers.feedgenerator import Atom1Feed
            feed = Atom1Feed(
                title=_(u'CKAN Dataset Revision History'),
                link=h.url_for(controller='revision', action='read', id=c.pkg_dict['name']),
                description=_(u'Recent changes to CKAN Dataset: ') + (c.pkg_dict['title'] or ''),
                language=unicode(get_lang()),
            )
            for revision_dict in c.pkg_revisions:
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
        return render('package/history.html')

    def new(self, data=None, errors=None, error_summary=None):
        
        package_type = request.path.strip('/').split('/')[0]
        if package_type == 'group':
            package_type = None
        
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'extras_as_string': True,
                   'save': 'save' in request.params,}

        # Package needs to have a publisher group in the call to check_access
        # and also to save it
        try:
            check_access('package_create',context)
        except NotAuthorized:
            abort(401, _('Unauthorized to create a package'))

        if context['save'] and not data:
            return self._save_new(context)

        data = data or clean_dict(unflatten(tuplize_dict(parse_params(
            request.params, ignore_keys=[CACHE_PARAMETER]))))

        errors = errors or {}
        error_summary = error_summary or {}
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary}

        self._setup_template_variables(context, {'id': id})

        # TODO: This check is to maintain backwards compatibility with the old way of creating
        # custom forms. This behaviour is now deprecated.
        if hasattr(self, 'package_form'):
            c.form = render(self.package_form, extra_vars=vars)
        else:
            c.form = render(self._package_form(package_type=package_type), extra_vars=vars)
        return render('package/new.html')


    def edit(self, id, data=None, errors=None, error_summary=None):
        package_type = self._get_package_type(id)
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'extras_as_string': True,
                   'save': 'save' in request.params,
                   'moderated': config.get('moderated'),
                   'pending': True,}

        if context['save'] and not data:
            return self._save_edit(id, context)
        try:
            old_data = get_action('package_show')(context, {'id':id})
            schema = self._db_to_form_schema(package_type=package_type)
            if schema and not data:
                old_data, errors = validate(old_data, schema, context=context)
            data = data or old_data
            # Merge all elements for the complete package dictionary
            c.pkg_dict = dict(old_data.items() + data.items())
        except NotAuthorized:
            abort(401, _('Unauthorized to read package %s') % '')
        except NotFound:
            abort(404, _('Dataset not found'))

        c.pkg = context.get("package")
        c.pkg_json = json.dumps(data)

        try:
            check_access('package_update',context)
        except NotAuthorized, e:
            abort(401, _('User %r not authorized to edit %s') % (c.user, id))

        errors = errors or {}
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary}

        self._setup_template_variables(context, {'id': id}, package_type=package_type)

        # TODO: This check is to maintain backwards compatibility with the old way of creating
        # custom forms. This behaviour is now deprecated.
        if hasattr(self, 'package_form'):
            c.form = render(self.package_form, extra_vars=vars)
        else:
            c.form = render(self._package_form(package_type=package_type), extra_vars=vars)
        return render('package/edit.html')

    def read_ajax(self, id, revision=None):
        package_type=self._get_package_type(id)
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'extras_as_string': True,
                   'schema': self._form_to_db_schema(package_type=package_type),
                   'revision_id': revision}

        try:
            data = get_action('package_show')(context, {'id': id})
            schema = self._db_to_form_schema(package_type=package_type)
            if schema:
                data, errors = validate(data, schema)
        except NotAuthorized:
            abort(401, _('Unauthorized to read package %s') % '')
        except NotFound:
            abort(404, _('Dataset not found'))

        ## hack as db_to_form schema should have this
        data['tag_string'] = ', '.join([tag['name'] for tag in data.get('tags', [])])
        data.pop('tags')
        data = flatten_to_string_key(data)
        response.headers['Content-Type'] = 'application/json;charset=utf-8'
        return json.dumps(data)

    def history_ajax(self, id):

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'extras_as_string': True,}
        data_dict = {'id':id}
        try:
            pkg_revisions = get_action('package_revision_list')(context, data_dict)
        except NotAuthorized:
            abort(401, _('Unauthorized to read package %s') % '')
        except NotFound:
            abort(404, _('Dataset not found'))


        data = []
        approved = False
        for num, revision in enumerate(pkg_revisions):
            if not approved and revision['approved_timestamp']:
                current_approved, approved = True, True
            else:
                current_approved = False
            
            data.append({'revision_id': revision['id'],
                         'message': revision['message'],
                         'timestamp': revision['timestamp'],
                         'author': revision['author'],
                         'approved': bool(revision['approved_timestamp']),
                         'current_approved': current_approved})
                
        response.headers['Content-Type'] = 'application/json;charset=utf-8'
        return json.dumps(data)

    def _get_package_type(self, id):
        """
        Given the id of a package it determines the plugin to load 
        based on the package's type name (type). The plugin found
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
            data = get_action('package_show')(context, {'id': id})
        except NotFound:
            abort(404, _('Dataset not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read package %s') % id)

        return data['type']

    def _save_new(self, context, package_type=None):
        from ckan.lib.search import SearchIndexError
        try:
            data_dict = clean_dict(unflatten(
                tuplize_dict(parse_params(request.POST))))
            data_dict['type'] = package_type
            context['message'] = data_dict.get('log_message', '')
            pkg = get_action('package_create')(context, data_dict)

            self._form_save_redirect(pkg['name'], 'new')
        except NotAuthorized:
            abort(401, _('Unauthorized to read package %s') % '')
        except NotFound, e:
            abort(404, _('Dataset not found'))
        except DataError:
            abort(400, _(u'Integrity Error'))
        except SearchIndexError, e:
            abort(500, _(u'Unable to add package to search index.') + repr(e.args))
        except ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.new(data_dict, errors, error_summary)

    def _save_edit(self, name_or_id, context):
        from ckan.lib.search import SearchIndexError
        try:
            data_dict = clean_dict(unflatten(
                tuplize_dict(parse_params(request.POST))))
            context['message'] = data_dict.get('log_message', '')
            if not context['moderated']:
                context['pending'] = False
            data_dict['id'] = name_or_id
            pkg = get_action('package_update')(context, data_dict)
            if request.params.get('save', '') == 'Approve':
                get_action('make_latest_pending_package_active')(context, data_dict)
            c.pkg = context['package']
            c.pkg_dict = pkg

            self._form_save_redirect(pkg['name'], 'edit')
        except NotAuthorized:
            abort(401, _('Unauthorized to read package %s') % id)
        except NotFound, e:
            abort(404, _('Dataset not found'))
        except DataError:
            abort(400, _(u'Integrity Error'))
        except SearchIndexError, e:
            abort(500, _(u'Unable to update search index.') + repr(e.args))
        except ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.edit(name_or_id, data_dict, errors, error_summary)

    def _form_save_redirect(self, pkgname, action):
        '''This redirects the user to the CKAN package/read page,
        unless there is request parameter giving an alternate location,
        perhaps an external website.
        @param pkgname - Name of the package just edited
        @param action - What the action of the edit was
        '''
        assert action in ('new', 'edit')
        if action == 'new':
            msg = _('<span class="new-dataset">Congratulations, your dataset has been created. ' \
                    '<a href="%s">Upload or link ' \
                    'some data now &raquo;</a></span>')
            msg = msg % h.url_for(controller='package', action='edit',
                    id=pkgname, anchor='section-resources')
            h.flash_success(msg,allow_html=True)
        url = request.params.get('return_to') or \
              config.get('package_%s_return_url' % action)
        if url:
            url = url.replace('<NAME>', pkgname)
        else:
            url = h.url_for(controller='package', action='read', id=pkgname)
        redirect(url)        
        
    def _adjust_license_id_options(self, pkg, fs):
        options = fs.license_id.render_opts['options']
        is_included = False
        for option in options:
            license_id = option[1]
            if license_id == pkg.license_id:
                is_included = True
        if not is_included:
            options.insert(1, (pkg.license_id, pkg.license_id))

    def authz(self, id):
        pkg = model.Package.get(id)
        if pkg is None:
            abort(404, gettext('Dataset not found'))
        c.pkg = pkg # needed to add in the tab bar to the top of the auth page
        c.pkgname = pkg.name
        c.pkgtitle = pkg.title
        try:
            context = {'model':model,'user':c.user or c.author, 'package':pkg}
            check_access('package_edit_permissions',context)
            c.authz_editable = True
            c.pkg_dict = get_action('package_show')(context, {'id': id})
        except NotAuthorized:
            c.authz_editable = False
        if not c.authz_editable:
            abort(401, gettext('User %r not authorized to edit %s authorizations') % (c.user, id))

        roles = self._handle_update_of_authz(pkg)
        self._prepare_authz_info_for_render(roles)
        return render('package/authz.html')

    def autocomplete(self):
        # DEPRECATED in favour of /api/2/util/dataset/autocomplete
        q = unicode(request.params.get('q', ''))
        if not len(q): 
            return ''

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author}

        data_dict = {'q':q}

        packages = get_action('package_autocomplete')(context,data_dict)

        pkg_list = []
        for pkg in packages:
            pkg_list.append('%s|%s' % (pkg['match_displayed'].replace('|', ' '), pkg['name']))
        return '\n'.join(pkg_list)

    def _render_edit_form(self, fs, params={}, clear_session=False):
        # errors arrive in c.error and fs.errors
        c.log_message = params.get('log_message', '')
        # rgrp: expunge everything from session before dealing with
        # validation errors) so we don't have any problematic saves
        # when the fs.render causes a flush.
        # seb: If the session is *expunged*, then the form can't be
        # rendered; I've settled with a rollback for now, which isn't
        # necessarily what's wanted here.
        # dread: I think this only happened with tags because until
        # this changeset, Tag objects were created in the Renderer
        # every time you hit preview. So I don't believe we need to
        # clear the session any more. Just in case I'm leaving it in
        # with the log comments to find out.
        if clear_session:
            # log to see if clearing the session is ever required
            if model.Session.new or model.Session.dirty or model.Session.deleted:
                log.warn('Expunging session changes which were not expected: '
                         '%r %r %r', (model.Session.new, model.Session.dirty,
                                      model.Session.deleted))
            try:
                model.Session.rollback()
            except AttributeError: # older SQLAlchemy versions
                model.Session.clear()
        edit_form_html = fs.render()
        c.form = h.literal(edit_form_html)
        return h.literal(render('package/edit_form.html'))

    def _update_authz(self, fs):
        validation = fs.validate()
        if not validation:
            c.form = self._render_edit_form(fs, request.params)
            raise ValidationException(fs)
        try:
            fs.sync()
        except Exception, inst:
            model.Session.rollback()
            raise
        else:
            model.Session.commit()

    def _person_email_link(self, name, email, reference):
        if email:
            if not name:
                name = email
            return h.mail_to(email_address=email, name=name, encode='javascript')
        else:
            if name:
                return name
            else:
                return reference + " unknown"

    def resource_read(self, id, resource_id):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author}

        try:
            c.resource = get_action('resource_show')(context, {'id': resource_id})
            c.package = get_action('package_show')(context, {'id': id})
            # required for nav menu
            c.pkg = context['package']
            c.resource_json = json.dumps(c.resource)
            c.pkg_dict = c.package
        except NotFound:
            abort(404, _('Resource not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read resource %s') % id)
        # get package license info
        license_id = c.package.get('license_id')
        try:
            c.package['isopen'] = model.Package.get_license_register()[license_id].isopen()
        except KeyError:
            c.package['isopen'] = False

        return render('package/resource_read.html')

