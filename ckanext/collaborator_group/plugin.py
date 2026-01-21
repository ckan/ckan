# -*- coding: utf-8 -*-

from ckan.common import CKANConfig
from ckan.lib.plugins import DefaultPermissionLabels
from ckan.types import Action, AuthFunction

import ckan.plugins as p
import ckan.model as model
import ckan.plugins.toolkit as tk

import ckanext.collaborator_group.views as views
import ckanext.collaborator_group.logic.action as action
import ckanext.collaborator_group.logic.auth as auth
import ckanext.collaborator_group.helpers as helpers

from ckanext.collaborator_group.cli import get_commands


class CollaboratorGroupPlugin(p.SingletonPlugin, DefaultPermissionLabels):
    p.implements(p.IConfigurer)
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)
    p.implements(p.IPermissionLabels)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IBlueprint)
    p.implements(p.IClick)

    # IConfigurer
    def update_config(self, config: CKANConfig):
        tk.add_template_directory(config, "templates")

    # IActions
    def get_actions(self) -> "dict[str, Action]":
        return {
            "package_collaborator_create_group": (
                action.package_collaborator_create_group
            ),
            "package_collaborator_delete_group": (
                action.package_collaborator_delete_group
            ),
            "package_collaborator_list_for_group": (
                action.package_collaborator_list_for_group
            ),
        }

    # IAuthFunctions
    def get_auth_functions(self) -> "dict[str, AuthFunction]":
        return {
            "package_collaborator_create_group": (
                auth.package_collaborator_create_group
            ),
            "package_collaborator_delete_group": (
                auth.package_collaborator_delete_group
            ),
            "package_update": auth.package_update,  # type: ignore
            "package_collaborator_list_for_group": (
                auth.package_collaborator_list_for_group
            ),
        }

    # IPermissionLabels
    def get_dataset_labels(self, dataset_obj: model.Package) -> "list[str]":
        labels = super(CollaboratorGroupPlugin, self).get_dataset_labels(
            dataset_obj
        )
        collaborator_group = tk.get_action(
            "package_collaborator_list_for_group"
        )({"ignore_auth": True}, {"id": dataset_obj.id})
        labels.extend("member-%s" % g["group_id"] for g in collaborator_group)
        return labels

    def get_user_dataset_labels(self, user_obj: model.User) -> "list[str]":
        labels = super(CollaboratorGroupPlugin, self).get_user_dataset_labels(
            user_obj
        )
        return labels

    # ITemplateHelpers
    def get_helpers(self):  # type: ignore
        return {
            "linked_group": helpers.linked_group,
            "get_collaborators_group": helpers.get_collaborators_group,
        }

    # IClick
    def get_commands(self):
        return get_commands()

    # IBlueprint
    def get_blueprint(self):
        return [views.collaborator_group]
