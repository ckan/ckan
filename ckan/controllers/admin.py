from pylons import config

import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.app_globals as app_globals
import ckan.model as model
import ckan.logic as logic
import ckan.new_authz

c = base.c
request = base.request
_ = base._

def get_sysadmins():
    q = model.Session.query(model.User).filter(model.User.sysadmin==True)
    return q.all()


class AdminController(base.BaseController):
    def __before__(self, action, **params):
        super(AdminController, self).__before__(action, **params)
        context = {'model': model,
                   'user': c.user, 'auth_user_obj': c.userobj}
        try:
            logic.check_access('sysadmin', context, {})
        except logic.NotAuthorized:
            base.abort(401, _('Need to be system administrator to administer'))
        c.revision_change_state_allowed = True

    def _get_config_form_items(self):
        # Styles for use in the form.select() macro.
        styles = [{'text': 'Default', 'value': '/base/css/main.css'},
                  {'text': 'Red', 'value': '/base/css/red.css'},
                  {'text': 'Green', 'value': '/base/css/green.css'},
                  {'text': 'Maroon', 'value': '/base/css/maroon.css'},
                  {'text': 'Fuchsia', 'value': '/base/css/fuchsia.css'}]

        homepages = [{'value': '1', 'text': 'Introductory area, search, featured group and featured organization'},
                     {'value': '2', 'text': 'Search, stats, introductory area, featured organization and featured group'},
                     {'value': '3', 'text': 'Search, introductory area and stats'}]

        items = [
            {'name': 'ckan.site_title', 'control': 'input', 'label': _('Site Title'), 'placeholder': ''},
            {'name': 'ckan.main_css', 'control': 'select', 'options': styles, 'label': _('Style'), 'placeholder': ''},
            {'name': 'ckan.site_description', 'control': 'input', 'label': _('Site Tag Line'), 'placeholder': ''},
            {'name': 'ckan.site_logo', 'control': 'input', 'label': _('Site Tag Logo'), 'placeholder': ''},
            {'name': 'ckan.site_about', 'control': 'markdown', 'label': _('About'), 'placeholder': _('About page text')},
            {'name': 'ckan.site_intro_text', 'control': 'markdown', 'label': _('Intro Text'), 'placeholder': _('Text on home page')},
            {'name': 'ckan.site_custom_css', 'control': 'textarea', 'label': _('Custom CSS'), 'placeholder': _('Customisable css inserted into the page header')},
            {'name': 'ckan.homepage_style', 'control': 'select', 'options': homepages, 'label': _('Homepage'), 'placeholder': ''},
        ]
        return items

    def reset_config(self):
        if 'cancel' in request.params:
            h.redirect_to(controller='admin', action='config')

        if request.method == 'POST':
            # remove sys info items
            for item in self._get_config_form_items():
                name = item['name']
                app_globals.delete_global(name)
            # reset to values in config
            app_globals.reset()
            h.redirect_to(controller='admin', action='config')

        return base.render('admin/confirm_reset.html')

    def config(self):

        items = self._get_config_form_items()
        data = request.POST
        if 'save' in data:
            # update config from form
            for item in items:
                name = item['name']
                if name in data:
                    app_globals.set_global(name, data[name])
            app_globals.reset()
            h.redirect_to(controller='admin', action='config')

        data = {}
        for item in items:
            name = item['name']
            data[name] = config.get(name)

        vars = {'data': data, 'errors': {}, 'form_items': items}
        return base.render('admin/config.html',
                           extra_vars = vars)

    def index(self):
        #now pass the list of sysadmins
        c.sysadmins = [a.name for a in get_sysadmins()]

        return base.render('admin/index.html')


    def trash(self):
        c.deleted_revisions = model.Session.query(
            model.Revision).filter_by(state=model.State.DELETED)
        c.deleted_packages = model.Session.query(
            model.Package).filter_by(state=model.State.DELETED)
        if not request.params or (len(request.params) == 1 and '__no_cache__'
                                  in request.params):
            return base.render('admin/trash.html')
        else:
            # NB: we repeat retrieval of of revisions
            # this is obviously inefficient (but probably not *that* bad)
            # but has to be done to avoid (odd) sqlalchemy errors (when doing
            # purge packages) of form: "this object already exists in the
            # session"
            msgs = []
            if ('purge-packages' in request.params) or ('purge-revisions' in
                                                        request.params):
                if 'purge-packages' in request.params:
                    revs_to_purge = []
                    for pkg in c.deleted_packages:
                        revisions = [x[0] for x in pkg.all_related_revisions]
                        # ensure no accidental purging of other(non-deleted)
                        # packages initially just avoided purging revisions
                        # where non-deleted packages were affected
                        # however this lead to confusing outcomes e.g.
                        # we succesfully deleted revision in which package
                        # was deleted (so package now active again) but no
                        # other revisions
                        problem = False
                        for r in revisions:
                            affected_pkgs = set(r.packages).\
                                difference(set(c.deleted_packages))
                            if affected_pkgs:
                                msg = _('Cannot purge package %s as '
                                        'associated revision %s includes '
                                        'non-deleted packages %s')
                                msg = msg % (pkg.id, r.id, [pkg.id for r
                                                            in affected_pkgs])
                                msgs.append(msg)
                                problem = True
                                break
                        if not problem:
                            revs_to_purge += [r.id for r in revisions]
                    model.Session.remove()
                else:
                    revs_to_purge = [rev.id for rev in c.deleted_revisions]
                revs_to_purge = list(set(revs_to_purge))
                for id in revs_to_purge:
                    revision = model.Session.query(model.Revision).get(id)
                    try:
                        # TODO deleting the head revision corrupts the edit
                        # page Ensure that whatever 'head' pointer is used
                        # gets moved down to the next revision
                        model.repo.purge_revision(revision, leave_record=False)
                    except Exception, inst:
                        msg = _('Problem purging revision %s: %s') % (id, inst)
                        msgs.append(msg)
                h.flash_success(_('Purge complete'))
            else:
                msgs.append(_('Action not implemented.'))

            for msg in msgs:
                h.flash_error(msg)
            h.redirect_to(controller='admin', action='trash')
