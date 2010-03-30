import sqlalchemy.orm
import simplejson

from ckan.lib.base import *
import ckan.model as model
import ckan.forms
from ckan.lib.search import Search, SearchOptions
import ckan.authz
import ckan.rating

class RestController(BaseController):

    def index(self):
        return render('rest/index')

    def list(self, register):
        if register == u'package':
            packages = model.Session.query(model.Package).all() 
            results = [package.name for package in packages]
            return self._finish_ok(results)
        elif register == u'group':
            groups = model.Session.query(model.Group).all() 
            results = [group.name for group in groups]
            return self._finish_ok(results)
        elif register == u'tag':
            tags = model.Session.query(model.Tag).all() #TODO
            results = [tag.name for tag in tags]
            return self._finish_ok(results)
        else:
            response.status_int = 400
            return ''

    def show(self, register, id):
        if register == u'revision':
            # Todo: Implement access control for revisions.
            rev = model.Session.query(model.Revision).get(id)
            if rev is None:
                response.status_int = 404
                return ''
            response_data = {
                'id': rev.id,
                'timestamp': model.strftimestamp(rev.timestamp),
                'author': rev.author,
                'message': rev.message,
            }
            return self._finish_ok(response_data)
        elif register == u'package':
            pkg = model.Package.by_name(id)
            if pkg is None:
                response.status_int = 404
                return ''

            if not self._check_access(pkg, model.Action.READ):
                return ''

            _dict = pkg.as_dict()
            #TODO check it's not none
            return self._finish_ok(_dict)
        elif register == u'group':
            group = model.Group.by_name(id)
            if group is None:
                response.status_int = 404
                return ''

            if not self._check_access(group, model.Action.READ):
                return ''

            _dict = group.as_dict()
            #TODO check it's not none
            return self._finish_ok(_dict)
        elif register == u'tag':
            obj = model.Tag.by_name(id) #TODO tags
            if obj is None:
                response.status_int = 404
                return ''            
            _dict = [pkgtag.package.name for pkgtag in obj.package_tags]
            return self._finish_ok(_dict)
        else:
            response.status_int = 400
            return ''

    def create(self, register):
        # Check an API key given
        if not self._check_access(None, None):
            return simplejson.dumps(_('Access denied'))
        try:
            request_data = self._get_request_data()
        except ValueError, inst:
            response.status_int = 400
            return gettext('JSON Error: %s') % str(inst)
        try:
            if register == 'package':
                fs = ckan.forms.package_fs
                request_fa_dict = ckan.forms.edit_package_dict(ckan.forms.get_package_dict(fs=fs), request_data)
                fs = fs.bind(model.Package, data=request_fa_dict, session=model.Session)
            elif register == 'group':
                request_fa_dict = ckan.forms.edit_group_dict(ckan.forms.get_group_dict(), request_data)
                fs = ckan.forms.group_fs_combined.bind(model.Group, data=request_fa_dict, session=model.Session)
            elif register == 'rating':
                return self._create_rating(request_data)
            else:
                response.status_int = 400
                return gettext('Cannot create new entity of this type: %s') % register
            validation = fs.validate()
            if not validation:
                response.status_int = 409
                return simplejson.dumps(repr(fs.errors))
            rev = model.repo.new_revision()
            rev.author = self.rest_api_user
            rev.message = _(u'REST API: Create object %s') % str(fs.name.value)
            fs.sync()

            # set default permissions
            if self.rest_api_user:
                admins = [model.User.by_name(self.rest_api_user.decode('utf8'))]
            else:
                admins = []
            model.setup_default_user_roles(fs.model, admins)

            model.repo.commit()        
        except Exception, inst:
            model.Session.rollback()
            raise
        obj = fs.model
        return self._finish_ok(obj.as_dict())
            
    def update(self, register, id):
        if register == 'package':
            entity = model.Package.by_name(id)
        elif register == 'group':
            entity = model.Group.by_name(id)
        else:
            reponse.status_int = 400
            return gettext('Cannot update entity of this type: %s') % register
        if not entity:
            response.status_int = 404
            return ''

        if not self._check_access(entity, model.Action.EDIT):
            return simplejson.dumps(_('Access denied'))

        try:
            request_data = self._get_request_data()
        except ValueError, inst:
            response.status_int = 400
            return gettext('JSON Error: %s') % str(inst)

        try:
            if register == 'package':
                fs = ckan.forms.package_fs
                orig_entity_dict = ckan.forms.get_package_dict(pkg=entity, fs=fs)
                request_fa_dict = ckan.forms.edit_package_dict(orig_entity_dict, request_data, id=entity.id)
            elif register == 'group':
                orig_entity_dict = ckan.forms.get_group_dict(entity)
                request_fa_dict = ckan.forms.edit_group_dict(orig_entity_dict, request_data, id=entity.id)
                fs = ckan.forms.group_fs_combined
            fs = fs.bind(entity, data=request_fa_dict)
            validation = fs.validate_on_edit(entity.name, entity.id)
            if not validation:
                response.status_int = 409
                return simplejson.dumps(repr(fs.errors))
            rev = model.repo.new_revision()
            rev.author = self.rest_api_user
            rev.message = _(u'REST API: Update object %s') % str(fs.name.value)
            fs.sync()

            model.repo.commit()        
        except Exception, inst:
            model.Session.rollback()
            if inst.__class__.__name__ == 'IntegrityError':
                response.status_int = 409
                return ''
            else:
                raise
        obj = fs.model
        return self._finish_ok(obj.as_dict())

    def delete(self, register, id):
        if register == 'package':
            entity = model.Package.by_name(id)
        elif register == 'group':
            entity = model.Group.by_name(id)
        else:
            reponse.status_int = 400
            return gettext('Cannot delete entity of this type: %s') % register
        if not entity:
            response.status_int = 404
            return ''

        if not self._check_access(entity, model.Action.PURGE):
            return simplejson.dumps(_('Access denied'))
            
        try:
            entity.delete()
            model.repo.commit()        
        except Exception, inst:
            raise

        return self._finish_ok()

    def search(self, register=None):
        if register == 'revision':
            if request.params.has_key('since_time'):
                since_time_str = request.params['since_time']
                since_time = model.strptimestamp(since_time_str)
                revs = model.Session.query(model.Revision).filter(model.Revision.timestamp>since_time)
            elif request.params.has_key('since_rev'):
                since_id = request.params['since_rev']
                revs = []
                for rev in model.Session.query(model.Revision).all():
                    if since_id == rev.id:
                        break
                    revs.append(rev)
            else:
                revs = model.Session.query(model.Revision).all()
            return self._finish_ok([rev.id for rev in revs])
        elif register == 'package':
            if request.params.has_key('qjson'):
                if not request.params['qjson']:
                    response.status_int = 400
                    return gettext('Blank qjson parameter')
                params = simplejson.loads(request.params['qjson'])
            elif request.params.values() and request.params.values() != [u''] and request.params.values() != [u'1']:
                params = request.params
            else:
                try:
                    params = self._get_request_data()
                except ValueError, inst:
                    response.status_int = 400
                    return gettext('Search params: %s') % str(inst)
                    
            options = SearchOptions(params)
            options.search_tags = False
            options.return_objects = False
            results = Search().run(options)
            return self._finish_ok(results)

    def tag_counts(self):
        tags = model.Session.query(model.Tag).all()
        results = []
        for tag in tags:
            tag_count = len(tag.package_tags)
            results.append((tag.name, tag_count))
        return self._finish_ok(results)

    def _create_rating(self, params):
        """ Example data:
               rating_opts = {'package':u'warandpeace',
                              'rating':5}
        """
        # check options
        package_name = params.get('package')
        rating = params.get('rating')
        user = self.rest_api_user
        opts_err = None
        if not package_name:
            opts_err = gettext('You must supply a package name (parameter "package").')
        elif not rating:
            opts_err = gettext('You must supply a rating (parameter "rating").')
        else:
            try:
                rating_int = int(rating)
            except ValueError:
                opts_err = gettext('Rating must be an integer value.')
            else:
                package = model.Package.by_name(package_name)
                if rating < ckan.rating.MIN_RATING or rating > ckan.rating.MAX_RATING:
                    opts_err = gettext('Rating must be between %i and %i.') % (ckan.rating.MIN_RATING, ckan.rating.MAX_RATING)
                elif not package:
                    opts_err = gettext('Package with name %r does not exist.') % package_name
        if opts_err:
            self.log.debug(opts_err)
            response.status_int = 400
            response.headers['Content-Type'] = 'application/json'
            return opts_err

        user = model.User.by_name(self.rest_api_user)
        ckan.rating.set_rating(user, package, rating_int)

        response.headers['Content-Type'] = 'application/json'
        package = model.Package.by_name(package_name)
        ret_dict = {'rating average':package.get_average_rating(),
                    'rating count': len(package.ratings)}
        return self._finish_ok(ret_dict)

    def _check_access(self, pkg, action):
        # Checks apikey is okay and user is authorized to do the specified
        # action on the specified package. If both args are None then just
        # the apikey is checked.
        api_key = None
        isOk = False
        keystr = request.environ.get('HTTP_AUTHORIZATION', None)
        if keystr is None:
            keystr = request.environ.get('Authorization', None)
        self.log.debug("Received API Key: %s" % keystr)
        api_key = model.Session.query(model.User).filter_by(apikey=unicode(keystr)).first()
        if api_key is not None:
            self.rest_api_user = api_key.name
        else:
            self.rest_api_user = ''

        if action and pkg:
            if action != model.Action.READ and self.rest_api_user in (model.PSEUDO_USER__VISITOR, ''):
                self.log.debug("Valid API key needed to make changes")
                response.status_int = 403
                response.headers['Content-Type'] = 'application/json'
                return False                
            
            am_authz = ckan.authz.Authorizer().is_authorized(self.rest_api_user, action, pkg)
            if not am_authz:
                self.log.debug("User is not authorized to %s %s" % (action, pkg))
                response.status_int = 403
                response.headers['Content-Type'] = 'application/json'
                return False
        elif not self.rest_api_user:
            self.log.debug("API key not authorized: %s" % keystr)
            response.status_int = 403
            response.headers['Content-Type'] = 'application/json'
            return False
        self.log.debug("Access OK.")
        response.status_int = 200
        return True                

    def _get_request_data(self):
        try:
            request_data = request.params.keys()[0]
        except Exception, inst:
            msg = _("Can't find entity data in request params %s: %s") % (
                request.params.items(), str(inst)
            )
            raise ValueError, msg
        request_data = simplejson.loads(request_data, encoding='utf8')
        # ensure unicode values
        for key, val in request_data.items():
            # if val is str then assume it is ascii, since simplejson converts
            # utf8 encoded JSON to unicode
            request_data[key] = self._make_unicode(val)
        return request_data
        
    def _make_unicode(self, entity):
        if isinstance(entity, str):
            return unicode(entity)
        elif isinstance(entity, list):
            new_items = []
            for item in entity:
                new_items.append(self._make_unicode(item))
            return new_items
        elif isinstance(entity, dict):
            new_dict = {}
            for key, val in entity.items():
                new_dict[key] = self._make_unicode(val)
            return new_dict
        else:
            return entity

    def _finish_ok(self, response_data=None):
        response.status_int = 200
        response.headers['Content-Type'] = 'application/json'
        if response_data:
            return simplejson.dumps(response_data)
        else:
            return ''

