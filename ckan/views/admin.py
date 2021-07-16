# encoding: utf-8

import logging

from flask import Blueprint
from flask.views import MethodView

import ckan.lib.app_globals as app_globals
import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.logic as logic
import ckan.model as model
from ckan.common import g, _, config, request
from ckan.views.home import CACHE_PARAMETERS


log = logging.getLogger(__name__)

admin = Blueprint('admin', __name__, url_prefix='/ckan-admin')


def _get_sysadmins():
    q = model.Session.query(model.User).filter(model.User.sysadmin.is_(True),
                                               model.User.state == 'active')
    return q


def _get_config_options():
    homepages = [{
        'value': '1',
        'text': ('Introductory area, search, featured'
                  ' group and featured organization')
    }, {
        'value': '2',
        'text': ('Search, stats, introductory area, '
                  'featured organization and featured group')
    }, {
        'value': '3',
        'text': 'Search, introductory area and stats'
    }]

    return dict(homepages=homepages)


def _get_config_items():
    return [
        'ckan.site_title', 'ckan.main_css', 'ckan.site_description',
        'ckan.site_logo', 'ckan.site_about', 'ckan.site_intro_text',
        'ckan.site_custom_css', 'ckan.homepage_style'
    ]


@admin.before_request
def before_request():
    try:
        context = dict(model=model, user=g.user, auth_user_obj=g.userobj)
        logic.check_access('sysadmin', context)
    except logic.NotAuthorized:
        base.abort(403, _('Need to be system administrator to administer'))


def index():
    data = dict(sysadmins=[a.name for a in _get_sysadmins()])
    return base.render('admin/index.html', extra_vars=data)


class ResetConfigView(MethodView):
    def get(self):
        if 'cancel' in request.args:
            return h.redirect_to('admin.config')
        return base.render('admin/confirm_reset.html', extra_vars={})

    def post(self):
        # remove sys info items
        for item in _get_config_items():
            model.delete_system_info(item)
        # reset to values in config
        app_globals.reset()
        return h.redirect_to('admin.config')


class ConfigView(MethodView):
    def get(self):
        items = _get_config_options()
        schema = logic.schema.update_configuration_schema()
        data = {}
        for key in schema:
            data[key] = config.get(key)

        vars = dict(data=data, errors={}, **items)

        return base.render('admin/config.html', extra_vars=vars)

    def post(self):
        try:
            req = request.form.copy()
            req.update(request.files.to_dict())
            data_dict = logic.clean_dict(
                dict_fns.unflatten(
                    logic.tuplize_dict(
                        logic.parse_params(req,
                                           ignore_keys=CACHE_PARAMETERS))))

            del data_dict['save']
            data = logic.get_action('config_option_update')({
                'user': g.user
            }, data_dict)

        except logic.ValidationError as e:
            items = _get_config_options()
            data = request.form
            errors = e.error_dict
            error_summary = e.error_summary
            vars = dict(data=data,
                        errors=errors,
                        error_summary=error_summary,
                        form_items=items,
                        **items)
            return base.render('admin/config.html', extra_vars=vars)

        return h.redirect_to('admin.config')


class TrashView(MethodView):
    def __init__(self):
        self.deleted_packages = model.Session.query(
            model.Package).filter_by(state=model.State.DELETED)
        self.deleted_orgs = model.Session.query(model.Group).filter_by(
            state=model.State.DELETED, is_organization=True)
        self.deleted_groups = model.Session.query(model.Group).filter_by(
            state=model.State.DELETED, is_organization=False)

        self.deleted_entities = {
            'package': self.deleted_packages,
            'organization': self.deleted_orgs,
            'group': self.deleted_groups
        }
        self.messages = {
            'confirm': {
                'all': _('Are you sure you want to purge everything?'),
                'package': _('Are you sure you want to purge datasets?'),
                'organization':
                    _('Are you sure you want to purge organizations?'),
                'group': _('Are you sure you want to purge groups?')
            },
            'success': {
                'package': _('{number} datasets have been purged'),
                'organization': _('{number} organizations have been purged'),
                'group': _('{number} groups have been purged')
            },
            'empty': {
                'package': _('There are no datasets to purge'),
                'organization': _('There are no organizations to purge'),
                'group': _('There are no groups to purge')
            }
        }

    def get(self):
        ent_type = request.args.get('name')

        if ent_type:
            return base.render('admin/snippets/confirm_delete.html',
                               extra_vars={
                                   'ent_type': ent_type,
                                   'messages': self.messages})

        data = dict(data=self.deleted_entities, messages=self.messages)
        return base.render('admin/trash.html', extra_vars=data)

    def post(self):
        if 'cancel' in request.form:
            return h.redirect_to('admin.trash')

        req_action = request.form.get('action')
        if req_action == 'all':
            self.purge_all()
        elif req_action in ('package', 'organization', 'group'):
            self.purge_entity(req_action)
        else:
            h.flash_error(_('Action not implemented.'))
        return h.redirect_to('admin.trash')

    def purge_all(self):
        actions = ('dataset_purge', 'group_purge', 'organization_purge')
        entities = (
            self.deleted_packages,
            self.deleted_groups,
            self.deleted_orgs
        )

        for action, deleted_entities in zip(actions, entities):
            for entity in deleted_entities:
                logic.get_action(action)(
                    {'user': g.user}, {'id': entity.id}
                )
            model.Session.remove()
        h.flash_success(_('Massive purge complete'))

    def purge_entity(self, ent_type):
        entities = self.deleted_entities[ent_type]
        number = entities.count()

        for ent in entities:
            logic.get_action(self._get_purge_action(ent_type))(
                {'user': g.user},
                {'id': ent.id}
            )

        model.Session.remove()
        h.flash_success(self.messages['success'][ent_type].format(
            number=number
        ))

    @staticmethod
    def _get_purge_action(ent_type):
        actions = {
            "package": "dataset_purge",
            "organization": "organization_purge",
            "group": "group_purge",
        }

        return actions.get(ent_type)


admin.add_url_rule(
    '/', view_func=index, methods=['GET'], strict_slashes=False
)
admin.add_url_rule('/reset_config',
                   view_func=ResetConfigView.as_view(str('reset_config')))
admin.add_url_rule('/config', view_func=ConfigView.as_view(str('config')))
admin.add_url_rule('/trash', view_func=TrashView.as_view(str('trash')))
