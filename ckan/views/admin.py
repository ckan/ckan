# encoding: utf-8
from __future__ import annotations

import logging
from typing import Any, Union, cast, List

from flask import Blueprint
from flask.views import MethodView
from flask.wrappers import Response

import ckan.lib.app_globals as app_globals
import ckan.lib.base as base
from ckan.lib.helpers import helper_functions as h
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.logic as logic
import ckan.model as model
import ckan.logic.schema
from ckan.common import _, config, request, current_user
from ckan.views.home import CACHE_PARAMETERS

from ckan.types import Context, Query


log = logging.getLogger(__name__)

admin = Blueprint(u'admin', __name__, url_prefix=u'/ckan-admin')


def _get_sysadmins() -> "Query[model.User]":
    q = model.Session.query(model.User).filter(
        # type_ignore_reason: incomplete SQLAlchemy types
        model.User.sysadmin.is_(True),  # type: ignore
        model.User.state == u'active')
    return q


def _get_config_options() -> dict[str, list[dict[str, str]]]:
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

    return dict(homepages=homepages)


def _get_config_items() -> list[str]:
    return [
        u'ckan.site_title', u'ckan.theme', u'ckan.site_description',
        u'ckan.site_logo', u'ckan.site_about', u'ckan.site_intro_text',
        u'ckan.site_custom_css', u'ckan.homepage_style'
    ]


@admin.before_request
def before_request() -> None:
    try:
        context = cast(
            Context, {
                "model": model,
                "user": current_user.name,
                "auth_user_obj": current_user
            }
        )
        logic.check_access(u'sysadmin', context)
    except logic.NotAuthorized:
        base.abort(403, _(u'Need to be system administrator to administer'))


def index() -> str:
    data = dict(sysadmins=[a.name for a in _get_sysadmins()])
    return base.render(u'admin/index.html', extra_vars=data)


class ResetConfigView(MethodView):
    def get(self) -> Union[str, Response]:
        if u'cancel' in request.args:
            return h.redirect_to(u'admin.config')
        return base.render(u'admin/confirm_reset.html', extra_vars={})

    def post(self) -> Response:
        # remove sys info items
        for item in _get_config_items():
            model.delete_system_info(item)
        # reset to values in config
        app_globals.reset()
        return h.redirect_to(u'admin.config')


class ConfigView(MethodView):
    def get(self) -> str:
        items = _get_config_options()
        schema = ckan.logic.schema.update_configuration_schema()
        data = {}
        for key in schema:
            data[key] = config.get(key)

        vars: dict[str, Any] = dict(data=data, errors={}, **items)

        return base.render(u'admin/config.html', extra_vars=vars)

    def post(self) -> Union[str, Response]:
        try:
            req: dict[str, Any] = request.form.copy()
            req.update(request.files.to_dict())
            data_dict = logic.clean_dict(
                dict_fns.unflatten(
                    logic.tuplize_dict(
                        logic.parse_params(req,
                                           ignore_keys=CACHE_PARAMETERS))))

            del data_dict['save']
            data = logic.get_action(u'config_option_update')({
                u'user': current_user.name
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
            return base.render(u'admin/config.html', extra_vars=vars)

        return h.redirect_to(u'admin.config')


class TrashView(MethodView):

    def __init__(self):
        self.deleted_packages = self._get_deleted_datasets()
        self.deleted_orgs = model.Session.query(model.Group).filter_by(
            state=model.State.DELETED, is_organization=True)
        self.deleted_groups = model.Session.query(model.Group).filter_by(
            state=model.State.DELETED, is_organization=False)

        self.deleted_entities = {
            u'package': self.deleted_packages,
            u'organization': self.deleted_orgs,
            u'group': self.deleted_groups
        }
        self.messages = {
            u'confirm': {
                u'all': _(u'Are you sure you want to purge everything?'),
                u'package': _(u'Are you sure you want to purge datasets?'),
                u'organization':
                    _(u'Are you sure you want to purge organizations?'),
                u'group': _(u'Are you sure you want to purge groups?')
            },
            u'success': {
                u'package': _(u'{number} datasets have been purged'),
                u'organization': _(u'{number} organizations have been purged'),
                u'group': _(u'{number} groups have been purged')
            },
            u'empty': {
                u'package': _(u'There are no datasets to purge'),
                u'organization': _(u'There are no organizations to purge'),
                u'group': _(u'There are no groups to purge')
            }
        }

    def _get_deleted_datasets(
        self
    ) -> Union["Query[model.Package]", List[Any]]:
        if config.get('ckan.search.remove_deleted_packages'):
            return self._get_deleted_datasets_from_db()
        else:
            return self._get_deleted_datasets_from_search_index()

    def _get_deleted_datasets_from_db(self) -> "Query[model.Package]":
        return model.Session.query(
            model.Package
        ).filter_by(
            state=model.State.DELETED
        )

    def _get_deleted_datasets_from_search_index(self) -> List[Any]:
        package_search = logic.get_action('package_search')
        search_params = {
            'fq': '+state:deleted',
            'include_private': True,
        }
        base_results = package_search(
            {'ignore_auth': True},
            search_params
        )

        return base_results['results']

    def get(self) -> str:
        ent_type = request.args.get(u'name')

        if ent_type:
            return base.render(u'admin/snippets/confirm_delete.html',
                               extra_vars={
                                   u'ent_type': ent_type,
                                   u'messages': self.messages})

        data = dict(data=self.deleted_entities, messages=self.messages)
        return base.render(u'admin/trash.html', extra_vars=data)

    def post(self) -> Response:
        if u'cancel' in request.form:
            return h.redirect_to(u'admin.trash')

        req_action = request.form.get(u'action', '')
        if req_action == u'all':
            self.purge_all()
        elif req_action in (u'package', u'organization', u'group'):
            self.purge_entity(req_action)
        else:
            h.flash_error(_(u'Action not implemented.'))
        return h.redirect_to(u'admin.trash')

    def purge_all(self):
        actions = (u'dataset_purge', u'group_purge', u'organization_purge')
        entities = (
            self.deleted_packages,
            self.deleted_groups,
            self.deleted_orgs
        )

        for action, deleted_entities in zip(actions, entities):
            for entity in deleted_entities:
                ent_id = entity.id if hasattr(entity, 'id') \
                    else entity['id']  # type: ignore
                logic.get_action(action)(
                    {u'user': current_user.name}, {u'id': ent_id}
                )
            model.Session.remove()
        h.flash_success(_(u'Massive purge complete'))

    def purge_entity(self, ent_type: str):
        entities = self.deleted_entities[ent_type]
        number = len(entities) if isinstance(entities, list) \
            else entities.count()

        for ent in entities:
            entity_id = ent.id if hasattr(ent, 'id') else ent['id']
            logic.get_action(self._get_purge_action(ent_type))(
                {u'user': current_user.name},
                {u'id': entity_id}
            )

        model.Session.remove()
        h.flash_success(self.messages[u'success'][ent_type].format(
            number=number
        ))

    @staticmethod
    def _get_purge_action(ent_type: str) -> str:
        actions = {
            "package": "dataset_purge",
            "organization": "organization_purge",
            "group": "group_purge",
        }

        return actions[ent_type]


admin.add_url_rule(
    u'/', view_func=index, methods=['GET'], strict_slashes=False
)
admin.add_url_rule(u'/reset_config',
                   view_func=ResetConfigView.as_view(str(u'reset_config')))
admin.add_url_rule(u'/config', view_func=ConfigView.as_view(str(u'config')))
admin.add_url_rule(u'/trash', view_func=TrashView.as_view(str(u'trash')))
