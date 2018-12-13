# encoding: utf-8

import logging

from ckan.controllers.home import CACHE_PARAMETERS
from flask import Blueprint
from flask.views import MethodView

import ckan.lib.app_globals as app_globals
import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.logic as logic
import ckan.model as model
from ckan.common import g, _, config, request

log = logging.getLogger(__name__)

admin = Blueprint(u'admin', __name__, url_prefix=u'/ckan-admin')


def _get_sysadmins():
    q = model.Session.query(model.User).filter(model.User.sysadmin.is_(True),
                                               model.User.state == u'active')
    return q


def _get_config_options():
    styles = [{
        u'text': u'Default',
        u'value': u'/base/css/main.css'
    }, {
        u'text': u'Red',
        u'value': u'/base/css/red.css'
    }, {
        u'text': u'Green',
        u'value': u'/base/css/green.css'
    }, {
        u'text': u'Maroon',
        u'value': u'/base/css/maroon.css'
    }, {
        u'text': u'Fuchsia',
        u'value': u'/base/css/fuchsia.css'
    }]

    homepages = [{
        u'value': u'1',
        u'text': (u'Introductory area, search, featured'
                  u' group and featured organization')
    }, {
        u'value': u'2',
        u'text': (u'Search, stats, introductory area, '
                  u'featured organization and featured group')
    }, {
        u'value': u'3',
        u'text': u'Search, introductory area and stats'
    }]

    return dict(styles=styles, homepages=homepages)


def _get_config_items():
    return [
        u'ckan.site_title', u'ckan.main_css', u'ckan.site_description',
        u'ckan.site_logo', u'ckan.site_about', u'ckan.site_intro_text',
        u'ckan.site_custom_css', u'ckan.homepage_style'
    ]


@admin.before_request
def before_request():
    try:
        context = dict(model=model, user=g.user, auth_user_obj=g.userobj)
        logic.check_access(u'sysadmin', context)
    except logic.NotAuthorized:
        base.abort(403, _(u'Need to be system administrator to administer'))


def index():
    data = dict(sysadmins=[a.name for a in _get_sysadmins()])
    return base.render(u'admin/index.html', extra_vars=data)


class ResetConfigView(MethodView):
    def get(self):
        if u'cancel' in request.args:
            return h.redirect_to(u'admin.config')
        return base.render(u'admin/confirm_reset.html', extra_vars={})

    def post(self):
        # remove sys info items
        for item in _get_config_items():
            model.delete_system_info(item)
        # reset to values in config
        app_globals.reset()
        return h.redirect_to(u'admin.config')


class ConfigView(MethodView):
    def get(self):
        items = _get_config_options()
        schema = logic.schema.update_configuration_schema()
        data = {}
        for key in schema:
            data[key] = config.get(key)

        vars = dict(data=data, errors={}, **items)

        return base.render(u'admin/config.html', extra_vars=vars)

    def post(self):
        try:
            req = request.form.copy()
            req.update(request.files.to_dict())
            data_dict = logic.clean_dict(
                dict_fns.unflatten(
                    logic.tuplize_dict(
                        logic.parse_params(
                            req, ignore_keys=CACHE_PARAMETERS))))

            del data_dict['save']
            data = logic.get_action(u'config_option_update')({
                u'user': g.user
            }, data_dict)

        except logic.ValidationError as e:
            items = _get_config_options()
            data = request.form
            errors = e.error_dict
            error_summary = e.error_summary
            vars = dict(
                data=data,
                errors=errors,
                error_summary=error_summary,
                form_items=items,
                **items)
            return base.render(u'admin/config.html', extra_vars=vars)

        return h.redirect_to(u'admin.config')


class TrashView(MethodView):
    def __init__(self):
        self.deleted_packages = model.Session.query(
            model.Package).filter_by(state=model.State.DELETED)

    def get(self):
        data = dict(deleted_packages=self.deleted_packages)
        return base.render(u'admin/trash.html', extra_vars=data)

    def post(self):
        deleted_revisions = model.Session.query(
            model.Revision).filter_by(state=model.State.DELETED)
        # NB: we repeat retrieval of of revisions
        # this is obviously inefficient (but probably not *that* bad)
        # but has to be done to avoid (odd) sqlalchemy errors (when doing
        # purge packages) of form: "this object already exists in the
        # session"
        msgs = []
        if (u'purge-packages' in request.form) or (
                u'purge-revisions' in request.form):
            if u'purge-packages' in request.form:
                revs_to_purge = []
                for pkg in self.deleted_packages:
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
                            difference(set(self.deleted_packages))
                        if affected_pkgs:
                            msg = _(u'Cannot purge package %s as '
                                    u'associated revision %s includes '
                                    u'non-deleted packages %s')
                            msg = msg % (pkg.id, r.id,
                                         [pkg.id for r in affected_pkgs])
                            msgs.append(msg)
                            problem = True
                            break
                    if not problem:
                        revs_to_purge += [r.id for r in revisions]
                model.Session.remove()
            else:
                revs_to_purge = [rev.id for rev in deleted_revisions]
            revs_to_purge = list(set(revs_to_purge))
            for id in revs_to_purge:
                revision = model.Session.query(model.Revision).get(id)
                try:
                    # TODO deleting the head revision corrupts the edit
                    # page Ensure that whatever 'head' pointer is used
                    # gets moved down to the next revision
                    model.repo.purge_revision(revision, leave_record=False)
                except Exception as inst:
                    msg = _(u'Problem purging revision %s: %s') % (id, inst)
                    msgs.append(msg)
            h.flash_success(_(u'Purge complete'))
        else:
            msgs.append(_(u'Action not implemented.'))

        for msg in msgs:
            h.flash_error(msg)
        return h.redirect_to(u'admin.trash')


admin.add_url_rule(u'/', view_func=index, strict_slashes=False)
admin.add_url_rule(
    u'/reset_config', view_func=ResetConfigView.as_view(str(u'reset_config')))
admin.add_url_rule(u'/config', view_func=ConfigView.as_view(str(u'config')))
admin.add_url_rule(u'/trash', view_func=TrashView.as_view(str(u'trash')))
