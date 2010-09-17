import logging
import urlparse

from sqlalchemy.orm import eagerload_all
from sqlalchemy import or_
import genshi
from pylons import config, cache
from pylons.i18n import get_lang, _

from ckan.lib.base import *
from ckan.lib.search import query_for, QueryOptions, SearchError
from ckan.lib.cache import proxy_cache
from ckan.lib.package_saver import PackageSaver, ValidationException
import ckan.forms
import ckan.authz
import ckan.rating
import ckan.misc

logger = logging.getLogger('ckan.controllers')

class PackageController(BaseController):
    authorizer = ckan.authz.Authorizer()

    def index(self):
        query = ckan.authz.Authorizer().authorized_query(c.user, model.Package)
        c.package_count = query.count()
        return render('package/index.html')

    @proxy_cache()
    def list(self):
        query = ckan.authz.Authorizer().authorized_query(c.user, model.Package)
        query = query.options(eagerload_all('package_tags.tag'))
        query = query.options(eagerload_all('package_resources_all'))
        c.page = h.AlphaPage(
            collection=query,
            page=request.params.get('page', 'A'),
            alpha_attribute='title',
            other_text=_('Other'),
        )
        return render('package/list.html')

    def search(self):        
        c.q = request.params.get('q') # unicode format (decoded from utf8)
        c.open_only = request.params.get('open_only')
        c.downloadable_only = request.params.get('downloadable_only')
        if c.q:
            c.query_error = False
            page = int(request.params.get('page', 1))
            limit = 20
            query = query_for(model.Package)
            try:
                query.run(query=c.q,
                          limit=limit,
                          offset=(page-1)*limit,
                          return_objects=True,
                          filter_by_openness=c.open_only,
                          filter_by_downloadable=c.downloadable_only,
                          username=c.user)
            
                c.page = h.Page(
                    collection=query.results,
                    page=page,
                    item_count=query.count,
                    items_per_page=limit
                )
                c.page.items = query.results
            except SearchError, se:
                c.query_error = True
                c.page = h.Page(collection=[])
            
            # tag search
            c.tag_limit = 25
            query = query_for('tag', backend='sql')
            try:
                query.run(query=c.q,
                          return_objects=True,
                          limit=c.tag_limit,
                          username=c.user)
                c.tags = query.results
                c.tags_count = query.count
            except SearchError, se:
                c.tags = []
                c.tags_count = 0

        return render('package/search.html')
    
    def _pkg_cache_key(self, pkg):
        # note: we need pkg.id in addition to pkg.revision.id because a
        # revision may have more than one package in it.
        return str(hash((pkg.id, pkg.revision.id, c.user, pkg.get_average_rating())))
        
    def _clear_pkg_cache(self, pkg):
        read_cache = cache.get_cache('package/read.html', type='dbm')
        read_cache.remove_value(self._pkg_cache_key(pkg))

    @proxy_cache()
    def read(self, id):
        pkg = model.Package.get(id)
        if pkg is None:
            abort(404, gettext('Package not found'))
        
        cache_key = self._pkg_cache_key(pkg)
        etag_cache(cache_key)
        
        # used by disqus plugin
        c.current_package_id = pkg.id
        
        if config.get('rdf_packages'):
            accept_headers = request.headers.get('Accept', '')
            if 'application/rdf+xml' in accept_headers and \
                   not 'text/html' in accept_headers:
                rdf_url = '%s%s' % (config['rdf_packages'], pkg.name)
                redirect(rdf_url, code=303)

        auth_for_read = self.authorizer.am_authorized(c, model.Action.READ, pkg)
        if not auth_for_read:
            abort(401, str(gettext('Unauthorized to read package %s') % id))

        c.auth_for_authz = self.authorizer.am_authorized(c, model.Action.EDIT_PERMISSIONS, pkg)
        c.auth_for_edit = self.authorizer.am_authorized(c, model.Action.EDIT, pkg)
        c.auth_for_change_state = self.authorizer.am_authorized(c, model.Action.CHANGE_STATE, pkg)

        PackageSaver().render_package(pkg)
        return render('package/read.html')

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
                h.redirect_to(controller='revision', action='diff', **params)

        c.pkg = model.Package.get(id)
        if not c.pkg:
            abort(404, gettext('Package not found'))
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

    def new(self):
        c.error = ''

        is_admin = self.authorizer.is_sysadmin(c.user)
        
        auth_for_create = self.authorizer.am_authorized(c, model.Action.CREATE, model.Package)
        if not auth_for_create:
            abort(401, str(gettext('Unauthorized to create a package')))
        
        fs = ckan.forms.registry.get_fieldset(is_admin=is_admin,
                         package_form=request.params.get('package_form'))
        if 'save' in request.params or 'preview' in request.params:
            if not request.params.has_key('log_message'):
                abort(400, ('Missing parameter: log_message'))
            log_message = request.params['log_message']

        record = model.Package
        if request.params.has_key('save'):
            fs = fs.bind(record, data=dict(request.params) or None, session=model.Session)
            try:
                PackageSaver().commit_pkg(fs, None, None, log_message, c.author)
                pkgname = fs.name.value

                pkg = model.Package.by_name(pkgname)
                admins = []
                if c.user:
                    user = model.User.by_name(c.user)
                    if user:
                        admins = [user]
                model.setup_default_user_roles(pkg, admins)
                model.repo.commit_and_remove()

                self._form_save_redirect(pkgname, 'new')
            except ValidationException, error:
                fs = error.args[0]
                c.form = self._render_edit_form(fs, request.params,
                        clear_session=True)
                return render('package/new.html')
            except KeyError, error:
                abort(400, ('Missing parameter: %s' % error.args).encode('utf8'))

        # use request params even when starting to allow posting from "outside"
        # (e.g. bookmarklet)
        if 'preview' in request.params or 'name' in request.params or 'url' in request.params:
            if 'name' not in request.params and 'url' in request.params:
                url = request.params.get('url')
                domain = urlparse.urlparse(url)[1]
                if domain.startswith('www.'):
                    domain = domain[4:]
            # ensure all fields specified in params (formalchemy needs this on bind)
            data = ckan.forms.add_to_package_dict(ckan.forms.get_package_dict(fs=fs), request.params)
            fs = fs.bind(model.Package, data=data, session=model.Session)
        else:
            fs = fs.bind(session=model.Session)
        c.form = self._render_edit_form(fs, request.params, clear_session=True)
        if 'preview' in request.params:
            try:
                PackageSaver().render_preview(fs, id, record.id,
                                              log_message=log_message,
                                              author=c.author)
                c.preview = h.literal(render('package/read_core.html'))
            except ValidationException, error:
                fs = error.args[0]
                c.form = self._render_edit_form(fs, request.params,
                        clear_session=True)
                return render('package/new.html')
        return render('package/new.html')

    def edit(self, id=None): # allow id=None to allow posting
        # TODO: refactor to avoid duplication between here and new
        c.error = ''

        pkg = model.Package.get(id)
        if pkg is None:
            abort(404, '404 Not Found')
        am_authz = self.authorizer.am_authorized(c, model.Action.EDIT, pkg)
        if not am_authz:
            abort(401, str(gettext('User %r not authorized to edit %s') % (c.user, id)))

        c.auth_for_change_state = self.authorizer.am_authorized(c, model.Action.CHANGE_STATE, pkg)
        fs = ckan.forms.registry.get_fieldset(is_admin=c.auth_for_change_state,
                       package_form=request.params.get('package_form'))

        if 'save' in request.params or 'preview' in request.params:
            if not request.params.has_key('log_message'):
                abort(400, ('Missing parameter: log_message'))
            log_message = request.params['log_message']

        if not 'save' in request.params and not 'preview' in request.params:
            # edit
            c.pkgname = pkg.name
            c.pkgtitle = pkg.title
            if pkg.license_id:
                self._adjust_license_id_options(pkg, fs)
            fs = fs.bind(pkg)
            c.form = self._render_edit_form(fs, request.params)
            return render('package/edit.html')
        elif request.params.has_key('save'):
            # id is the name (pre-edited state)
            pkgname = id
            params = dict(request.params) # needed because request is nested
                                          # multidict which is read only
            fs = fs.bind(pkg, data=params or None)
            try:
                PackageSaver().commit_pkg(fs, id, pkg.id, log_message, c.author)
                # do not use package name from id, as it may have been edited
                pkgname = fs.name.value
                self._form_save_redirect(pkgname, 'edit')
            except ValidationException, error:
                fs = error.args[0]
                c.form = self._render_edit_form(fs, request.params,
                        clear_session=True)
                return render('package/edit.html')
            except KeyError, error:
                abort(400, 'Missing parameter: %s' % error.args)
        else: # Must be preview
            c.pkgname = pkg.name
            c.pkgtitle = pkg.title
            if pkg.license_id:
                self._adjust_license_id_options(pkg, fs)
            fs = fs.bind(pkg, data=dict(request.params))
            try:
                PackageSaver().render_preview(fs, id, pkg.id,
                                              log_message=log_message,
                                              author=c.author)
                c.pkgname = fs.name.value
                c.pkgtitle = fs.title.value
                read_core_html = render('package/read_core.html') #utf8 format
                c.preview = h.literal(read_core_html)
                c.form = self._render_edit_form(fs, request.params)
            except ValidationException, error:
                fs = error.args[0]
                c.form = self._render_edit_form(fs, request.params,
                        clear_session=True)
                return render('package/edit.html')
            return render('package/edit.html') # uses c.form and c.preview

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
            url = h.url_for(action='read', id=pkgname)
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
            abort(401, str(gettext('User %r not authorized to edit %s authorizations') % (c.user, id)))

        if 'save' in request.params: # form posted
            # needed because request is nested
            # multidict which is read only
            params = dict(request.params)
            c.fs = ckan.forms.get_authz_fieldset('package_authz_fs').bind(pkg.roles, data=params or None)
            try:
                self._update_authz(c.fs)
            except ValidationException, error:
                # TODO: sort this out 
                # fs = error.args
                # return render('package/authz.html')
                raise
            # now do new roles
            newrole_user_id = request.params.get('PackageRole--user_id')
            if newrole_user_id != '__null_value__':
                user = model.Session.query(model.User).get(newrole_user_id)
                # TODO: chech user is not None (should go in validation ...)
                role = request.params.get('PackageRole--role')
                newpkgrole = model.PackageRole(user=user, package=pkg,
                        role=role)
                # With FA no way to get new PackageRole back to set package attribute
                # new_roles = ckan.forms.new_roles_fs.bind(model.PackageRole, data=params or None)
                # new_roles.sync()
                model.repo.commit_and_remove()
                c.message = _(u'Added role \'%s\' for user \'%s\'') % (
                    newpkgrole.role,
                    newpkgrole.user.name)
        elif 'role_to_delete' in request.params:
            pkgrole_id = request.params['role_to_delete']
            pkgrole = model.Session.query(model.PackageRole).get(pkgrole_id)
            if pkgrole is None:
                c.error = _(u'Error: No role found with that id')
            else:
                c.message = _(u'Deleted role \'%s\' for user \'%s\'') % (pkgrole.role,
                        pkgrole.user.name)
                pkgrole.purge()
                model.repo.commit_and_remove()

        # retrieve pkg again ...
        c.pkg = model.Package.get(id)
        fs = ckan.forms.get_authz_fieldset('package_authz_fs').bind(c.pkg.roles)
        c.form = fs.render()
        c.new_roles_form = ckan.forms.get_authz_fieldset('new_package_roles_fs').render()
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
        # expunge everything from session so we don't have any problematic
        # saves (this gets called on validation exceptions a lot)
        if clear_session:
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
