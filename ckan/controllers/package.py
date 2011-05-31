import logging
import urlparse
from urllib import urlencode

from sqlalchemy.orm import eagerload_all
from sqlalchemy import or_
import genshi
from pylons import config, cache
from pylons.i18n import get_lang, _
from autoneg.accept import negotiate

import ckan.logic.action.create as create
import ckan.logic.action.update as update
import ckan.logic.action.get as get
from ckan.logic.schema import package_form_schema
from ckan.lib.base import request, c, BaseController, model, abort, h, g, render
from ckan.lib.base import etag_cache, response, redirect, gettext
from ckan.authz import Authorizer
from ckan.lib.search import query_for, SearchError
from ckan.lib.cache import proxy_cache
from ckan.lib.package_saver import PackageSaver, ValidationException
from ckan.lib.navl.dictization_functions import DataError, unflatten, validate
from ckan.logic import NotFound, NotAuthorized, ValidationError
from ckan.logic import tuplize_dict, clean_dict, parse_params
from ckan.plugins import PluginImplementations, IPackageController
import ckan.forms
import ckan.authz
import ckan.rating
import ckan.misc

log = logging.getLogger('ckan.controllers')

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

    ## hooks for subclasses 
    package_form = 'package/new_package_form.html'

    def _form_to_db_schema(self):
        return package_form_schema()

    def _db_to_form_schema(self):
        '''This is an interface to manipulate data from the database
        into a format suitable for the form (optional)'''

    def _check_data_dict(self, data_dict):
        '''Check if the return data is correct, mostly for checking out if
        spammers are submitting only part of the form'''

        surplus_keys_schema = ['__extras', '__junk', 'state', 'groups',
                               'extras_validation', 'save', 'preview',
                               'return_to']

        schema_keys = package_form_schema().keys()
        keys_in_schema = set(schema_keys) - set(surplus_keys_schema)

        if keys_in_schema - set(data_dict.keys()):
            log.info('incorrect form fields posted')
            raise DataError(data_dict)

    def _setup_template_variables(self, context):
        c.groups = get.group_list_availible(context)
        c.groups_authz = get.group_list_authz(context)
        c.licences = [('', '')] + model.Package.get_license_options()
        c.is_sysadmin = Authorizer().is_sysadmin(c.user)
        c.resource_columns = model.Resource.get_columns()

        ## This is messy as auths take domain object not data_dict
        pkg = context.get('package') or c.pkg
        if pkg:
            c.auth_for_change_state = Authorizer().am_authorized(
                c, model.Action.CHANGE_STATE, pkg)

    ## end hooks

    authorizer = ckan.authz.Authorizer()
    extensions = PluginImplementations(IPackageController)

    def search(self):        
        if not self.authorizer.am_authorized(c, model.Action.SITE_READ, model.System):
            abort(401, _('Not authorized to see this page'))
        q = c.q = request.params.get('q') # unicode format (decoded from utf8)
        c.open_only = request.params.get('open_only')
        c.downloadable_only = request.params.get('downloadable_only')
        c.query_error = False
        try:
            page = int(request.params.get('page', 1))
        except ValueError, e:
            abort(400, ('"page" parameter must be an integer'))
        limit = 20
        query = query_for(model.Package)

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
            for (param, value) in request.params.items():
                if not param in ['q', 'open_only', 'downloadable_only', 'page'] \
                        and len(value) and not param.startswith('_'):
                    c.fields.append((param, value))

            query.run(query=q,
                      fields=c.fields,
                      facet_by=g.facets,
                      limit=limit,
                      offset=(page-1)*limit,
                      return_objects=True,
                      filter_by_openness=c.open_only,
                      filter_by_downloadable=c.downloadable_only,
                      username=c.user)
                       
            c.page = h.Page(
                collection=query.results,
                page=page,
                url=pager_url,
                item_count=query.count,
                items_per_page=limit
            )
            c.facets = query.facets
            c.page.items = query.results
        except SearchError, se:
            c.query_error = True
            c.facets = {}
            c.page = h.Page(collection=[])
        
        return render('package/search.html')

    @staticmethod
    def _pkg_cache_key(pkg):
        # note: we need pkg.id in addition to pkg.revision.id because a
        # revision may have more than one package in it.
        return str(hash((pkg.id, pkg.latest_related_revision.id, c.user, pkg.get_average_rating())))

    def _clear_pkg_cache(self, pkg):
        read_cache = cache.get_cache('package/read.html', type='dbm')
        read_cache.remove_value(self._pkg_cache_key(pkg))

    @proxy_cache()
    def read(self, id):
        
        #check if package exists
        c.pkg = model.Package.get(id)
        if c.pkg is None:
            abort(404, _('Package not found'))
        
        cache_key = self._pkg_cache_key(c.pkg)        
        etag_cache(cache_key)
        
        #set a cookie so we know whether to display the welcome message
        c.hide_welcome_message = bool(request.cookies.get('hide_welcome_message', False))
        response.set_cookie('hide_welcome_message', '1', max_age=3600) #(make cross-site?)

        # used by disqus plugin
        c.current_package_id = c.pkg.id
        
        if config.get('rdf_packages'):
            accept_header = request.headers.get('Accept', '*/*')
            for content_type, exts in negotiate(autoneg_cfg, accept_header):
                if "html" not in exts: 
                    rdf_url = '%s%s.%s' % (config['rdf_packages'], c.pkg.id, exts[0])
                    redirect(rdf_url, code=303)
                break
            
        #is the user allowed to see this package?
        auth_for_read = self.authorizer.am_authorized(c, model.Action.READ, c.pkg)
        if not auth_for_read:
            abort(401, _('Unauthorized to read package %s') % id)
        
        for item in self.extensions:
            item.read(c.pkg)

        #render the package
        PackageSaver().render_package(c.pkg)
        return render('package/read.html')

    def comments(self, id):

        #check if package exists
        c.pkg = model.Package.get(id)
        if c.pkg is None:
            abort(404, _('Package not found'))

        # used by disqus plugin
        c.current_package_id = c.pkg.id

        #is the user allowed to see this package?
        auth_for_read = self.authorizer.am_authorized(c, model.Action.READ, c.pkg)
        if not auth_for_read:
            abort(401, _('Unauthorized to read package %s') % id)

        for item in self.extensions:
            item.read(c.pkg)

        #render the package
        PackageSaver().render_package(c.pkg)
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

        c.pkg = model.Package.get(id)
        if not c.pkg:
            abort(404, _('Package not found'))
        format = request.params.get('format', '')
        if format == 'atom':
            # Generate and return Atom 1.0 document.
            from webhelpers.feedgenerator import Atom1Feed
            feed = Atom1Feed(
                title=_(u'CKAN Package Revision History'),
                link=h.url_for(controller='revision', action='read', id=c.pkg.name),
                description=_(u'Recent changes to CKAN Package: ') + (c.pkg.title or ''),
                language=unicode(get_lang()),
            )
            for revision, obj_rev in c.pkg.all_related_revisions:
                try:
                    dayHorizon = int(request.params.get('days'))
                except:
                    dayHorizon = 30
                try:
                    dayAge = (datetime.now() - revision.timestamp).days
                except:
                    dayAge = 0
                if dayAge >= dayHorizon:
                    break
                if revision.message:
                    item_title = u'%s' % revision.message.split('\n')[0]
                else:
                    item_title = u'%s' % revision.id
                item_link = h.url_for(controller='revision', action='read', id=revision.id)
                item_description = _('Log message: ')
                item_description += '%s' % (revision.message or '')
                item_author_name = revision.author
                item_pubdate = revision.timestamp
                feed.add_item(
                    title=item_title,
                    link=item_link,
                    description=item_description,
                    author_name=item_author_name,
                    pubdate=item_pubdate,
                )
            feed.content_type = 'application/atom+xml'
            return feed.writeString('utf-8')
        c.pkg_revisions = c.pkg.all_related_revisions
        return render('package/history.html')

    def new(self, data=None, errors=None, error_summary=None):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'extras_as_string': True,
                   'preview': 'preview' in request.params,
                   'save': 'save' in request.params,
                   'schema': self._form_to_db_schema()}

        auth_for_create = Authorizer().am_authorized(c, model.Action.PACKAGE_CREATE, model.System())
        if not auth_for_create:
            abort(401, _('Unauthorized to create a package'))

        if (context['save'] or context['preview']) and not data:
            return self._save_new(context)

        data = data or {}
        errors = errors or {}
        error_summary = error_summary or {}
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary}

        self._setup_template_variables(context)
        c.form = render(self.package_form, extra_vars=vars)
        return render('package/new.html')


    def edit(self, id, data=None, errors=None, error_summary=None):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'extras_as_string': True,
                   'preview': 'preview' in request.params,
                   'save': 'save' in request.params,
                   'id': id,
                   'schema': self._form_to_db_schema()}

        if (context['save'] or context['preview']) and not data:
            return self._save_edit(id, context)

        try:
            old_data = get.package_show(context)
            schema = self._db_to_form_schema()
            if schema:
                old_data, errors = validate(old_data, schema)
            data = data or old_data
        except NotAuthorized:
            abort(401, _('Unauthorized to read package %s') % '')

        c.pkg = context.get("package")

        am_authz = self.authorizer.am_authorized(c, model.Action.EDIT, c.pkg)
        if not am_authz:
            abort(401, _('User %r not authorized to edit %s') % (c.user, id))

        errors = errors or {}
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary}

        self._setup_template_variables(context)
        c.form = render(self.package_form, extra_vars=vars)
        return render('package/edit.html')

    def _save_new(self, context):
        try:
            data_dict = clean_dict(unflatten(
                tuplize_dict(parse_params(request.params))))
            self._check_data_dict(data_dict)
            context['message'] = data_dict.get('log_message', '')
            pkg = create.package_create(data_dict, context)

            if context['preview']:
                PackageSaver().render_package(context['package'])
                c.is_preview = True
                c.preview = render('package/read_core.html')
                return self.new(data_dict)

            self._form_save_redirect(pkg['name'], 'new')
        except NotAuthorized:
            abort(401, _('Unauthorized to read package %s') % '')
        except NotFound, e:
            abort(404, _('Package not found'))
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
            self._check_data_dict(data_dict)
            context['message'] = data_dict.get('log_message', '')
            pkg = update.package_update(data_dict, context)
            c.pkg = context['package']

            if context['preview']:
                c.is_preview = True
                PackageSaver().render_package(context['package'])
                c.preview = render('package/read_core.html')
                return self.edit(id, data_dict)

            self._form_save_redirect(pkg['name'], 'edit')
        except NotAuthorized:
            abort(401, _('Unauthorized to read package %s') % id)
        except NotFound, e:
            abort(404, _('Package not found'))
        except DataError:
            abort(400, _(u'Integrity Error'))
        except ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.edit(id, data_dict, errors, error_summary)

    def _form_save_redirect(self, pkgname, action):
        '''This redirects the user to the CKAN package/read page,
        unless there is request parameter giving an alternate location,
        perhaps an external website.
        @param pkgname - Name of the package just edited
        @param action - What the action of the edit was
        '''
        assert action in ('new', 'edit')
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
            abort(404, gettext('Package not found'))
        c.pkgname = pkg.name
        c.pkgtitle = pkg.title

        c.authz_editable = self.authorizer.am_authorized(c, model.Action.EDIT_PERMISSIONS, pkg)
        if not c.authz_editable:
            abort(401, gettext('User %r not authorized to edit %s authorizations') % (c.user, id))

        # Three different ways of getting the list of userobjectroles for this package.
        # They all take a frighteningly long time to retrieve
        # the data, but I can't tell how they'll scale. On a large dataset it might
        # be worth working out which is quickest, so I've made a function for
        # ease of changing the query.
        def get_userobjectroles():
            # we already have a pkg variable in scope, but I found while testing
            # that it occasionally mysteriously loses its value!  Redefine it
            # here. 
            pkg = model.Package.get(id)

            # dread's suggestion for 'get all userobjectroles for this package':
            uors = model.Session.query(model.PackageRole).join('package').filter_by(name=pkg.name).all()
            # rgrp's version:
            # uors = model.Session.query(model.PackageRole).filter_by(package=pkg)
            # get them all and filter in python:
            # uors = [uor for uor in model.Session.query(model.PackageRole).all() if uor.package==pkg]
            return uors

        def action_save_form(users_or_authz_groups):
            # The permissions grid has been saved
            # which is a grid of checkboxes named user$role
            rpi = request.params.items()

            # The grid passes us a list of the users/roles that were displayed
            submitted = [ a for (a,b) in rpi if (b == u'submitted')]
            # and also those which were checked
            checked = [ a for (a,b) in rpi if (b == u'on')]

            # from which we can deduce true/false for each user/role combination
            # that was displayed in the form
            table_dict={}
            for a in submitted:
                table_dict[a]=False
            for a in checked:
                table_dict[a]=True

            # now we'll split up the user$role strings to make a dictionary from 
            # (user,role) to True/False, which tells us what we need to do.
            new_user_role_dict={}
            for (ur,val) in table_dict.items():
                u,r = ur.split('$')
                new_user_role_dict[(u,r)] = val
               
            # we get the current user/role assignments 
            # and make a dictionary of them
            current_uors = get_userobjectroles()

            if users_or_authz_groups=='users':
                current_users_roles = [( uor.user.name, uor.role) for uor in current_uors if uor.user]
            elif users_or_authz_groups=='authz_groups':
                current_users_roles = [( uor.authorized_group.name, uor.role) for uor in current_uors if uor.authorized_group]        
            else:
                assert False, "shouldn't be here"

            current_user_role_dict={}
            for (u,r) in current_users_roles:
                current_user_role_dict[(u,r)]=True

            # and now we can loop through our dictionary of desired states
            # checking whether a change needs to be made, and if so making it

            # Here we check whether someone is already assigned a role, in order
            # to avoid assigning it twice, or attempting to delete it when it
            # doesn't exist. Otherwise problems can occur.
            if users_or_authz_groups=='users':
                for ((u,r), val) in new_user_role_dict.items():
                    if val:
                        if not ((u,r) in current_user_role_dict):
                            model.add_user_to_role(model.User.by_name(u),r,pkg)
                    else:
                        if ((u,r) in current_user_role_dict):
                            model.remove_user_from_role(model.User.by_name(u),r,pkg)
            elif users_or_authz_groups=='authz_groups':
                for ((u,r), val) in new_user_role_dict.items():
                    if val:
                        if not ((u,r) in current_user_role_dict):
                            model.add_authorization_group_to_role(model.AuthorizationGroup.by_name(u),r,pkg)
                    else:
                        if ((u,r) in current_user_role_dict):
                            model.remove_authorization_group_from_role(model.AuthorizationGroup.by_name(u),r,pkg)
            else:
                assert False, "shouldn't be here"


            # finally commit the change to the database
            model.repo.commit_and_remove()
            h.flash_success("Changes Saved")



        def action_add_form(users_or_authz_groups):
            # The user is attempting to set new roles for a named user
            new_user = request.params.get('new_user_name')
            # this is the list of roles whose boxes were ticked
            checked_roles = [ a for (a,b) in request.params.items() if (b == u'on')]
            # this is the list of all the roles that were in the submitted form
            submitted_roles = [ a for (a,b) in request.params.items() if (b == u'submitted')]

            # from this we can make a dictionary of the desired states
            # i.e. true for the ticked boxes, false for the unticked
            desired_roles = {}
            for r in submitted_roles:
                desired_roles[r]=False
            for r in checked_roles:
                desired_roles[r]=True

            # again, in order to avoid either creating a role twice or deleting one which is
            # non-existent, we need to get the users' current roles (if any)
  
            current_uors = get_userobjectroles()

            if users_or_authz_groups=='users':
                current_roles = [uor.role for uor in current_uors if ( uor.user and uor.user.name == new_user )]
                user_object = model.User.by_name(new_user)
                if user_object==None:
                    # The submitted user does not exist. Bail with flash message
                    h.flash_error('unknown user:' + str (new_user))
                else:
                    # Whenever our desired state is different from our current state, change it.
                    for (r,val) in desired_roles.items():
                        if val:
                            if (r not in current_roles):
                                model.add_user_to_role(user_object, r, pkg)
                        else:
                            if (r in current_roles):
                                model.remove_user_from_role(user_object, r, pkg)
                    h.flash_success("User Added")

            elif users_or_authz_groups=='authz_groups':
                current_roles = [uor.role for uor in current_uors if ( uor.authorized_group and uor.authorized_group.name == new_user )]
                user_object = model.AuthorizationGroup.by_name(new_user)
                if user_object==None:
                    # The submitted user does not exist. Bail with flash message
                    h.flash_error('unknown authorization group:' + str (new_user))
                else:
                    # Whenever our desired state is different from our current state, change it.
                    for (r,val) in desired_roles.items():
                        if val:
                            if (r not in current_roles):
                                model.add_authorization_group_to_role(user_object, r, pkg)
                        else:
                            if (r in current_roles):
                                model.remove_authorization_group_from_role(user_object, r, pkg)
                    h.flash_success("Authorization Group Added")

            else:
                assert False, "shouldn't be here"

            # and finally commit all these changes to the database
            model.repo.commit_and_remove()


        # In the event of a post request, work out which of the four possible actions
        # is to be done, and do it before displaying the page
        if 'add' in request.POST:
            action_add_form('users')

        if 'authz_add' in request.POST:
            action_add_form('authz_groups')

        if 'save' in request.POST:
            action_save_form('users')

        if 'authz_save' in request.POST:
            action_save_form('authz_groups')

        # =================
        # Display the page

        # Find out all the possible roles. At the moment, any role can be
        # associated with any object, so that's easy:
        possible_roles = model.Role.get_all()

        # get the list of users who have roles on this object, with their roles
        uors = get_userobjectroles()

        # uniquify and sort
        users = sorted(list(set([uor.user.name for uor in uors if uor.user])))
        authz_groups = sorted(list(set([uor.authorized_group.name for uor in uors if uor.authorized_group])))

        # make a dictionary from (user, role) to True, False
        users_roles = [( uor.user.name, uor.role) for uor in uors if uor.user]
        user_role_dict={}
        for u in users:
            for r in possible_roles:
                if (u,r) in users_roles:
                    user_role_dict[(u,r)]=True
                else:
                    user_role_dict[(u,r)]=False

        # and similarly make a dictionary from (authz_group, role) to True, False
        authz_groups_roles = [( uor.authorized_group.name, uor.role) for uor in uors if uor.authorized_group]
        authz_groups_role_dict={}
        for u in authz_groups:
            for r in possible_roles:
                if (u,r) in authz_groups_roles:
                    authz_groups_role_dict[(u,r)]=True
                else:
                    authz_groups_role_dict[(u,r)]=False

        # pass these variables to the template for rendering
        c.roles = possible_roles

        c.users = users
        c.user_role_dict = user_role_dict

        c.authz_groups = authz_groups
        c.authz_groups_role_dict = authz_groups_role_dict

        return render('package/authz.html')




    def rate(self, id):
        package_name = id
        package = model.Package.get(package_name)
        if package is None:
            abort(404, gettext('404 Package Not Found'))
        self._clear_pkg_cache(package)
        rating = request.params.get('rating', '')
        if rating:
            try:
                ckan.rating.set_my_rating(c, package, rating)
            except ckan.rating.RatingValueException, e:
                abort(400, gettext('Rating value invalid'))
        h.redirect_to(controller='package', action='read', id=package_name, rating=str(rating))

    def autocomplete(self):
        q = unicode(request.params.get('q', ''))
        if not len(q): 
            return ''
        pkg_list = []
        like_q = u"%s%%" % q
        pkg_query = ckan.authz.Authorizer().authorized_query(c.user, model.Package)
        pkg_query = pkg_query.filter(or_(model.Package.name.ilike(like_q),
                                         model.Package.title.ilike(like_q)))
        pkg_query = pkg_query.limit(10)
        for pkg in pkg_query:
            if pkg.name.lower().startswith(q.lower()):
                pkg_list.append('%s|%s' % (pkg.name, pkg.name))
            else:
                pkg_list.append('%s (%s)|%s' % (pkg.title.replace('|', ' '), pkg.name, pkg.name))
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
