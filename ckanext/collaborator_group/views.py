import ckan.logic as logic
import ckan.model as model
import ckan.plugins.toolkit as tk
import ckan.lib.helpers as h
import ckan.authz as authz
import ckan.lib.navl.dictization_functions as dict_fns

from ckan.common import g, request
from ckan.types import Context, Response

from typing import Any, Union, cast
from flask.views import MethodView
from flask import Blueprint


collaborator_group = Blueprint('collaborator_group', __name__)


def collaborator_delete():
    pass


class CollaboratorEditView(MethodView):

    def post(self, id: str) -> Response:  # noqa
        context = cast(Context, {u'model': model, u'user': g.user})
        data_dict = dict()

        try:
            form_dict = logic.clean_dict(
                dict_fns.unflatten(
                    logic.tuplize_dict(
                        logic.parse_params(request.form))))

            if form_dict['group']:
                group = logic.get_action(u'group_show')(
                    context, {'id': form_dict['group']}
                )
                data_dict: dict[str, Any] = {
                    u'id': id,
                    u'group_id': group['id'],
                    u'capacity': form_dict['capacity']
                }

                logic.get_action(u'package_collaborator_create_group')(
                    context, data_dict)

            else:
                user = logic.get_action(u'user_show')(
                    context, {u'id': form_dict[u'username']}
                )

                data_dict: dict[str, Any] = {
                    u'id': id,
                    u'user_id': user[u'id'],
                    u'capacity': form_dict[u'capacity']
                }

                logic.get_action(u'package_collaborator_create')(
                    context, data_dict)

        except dict_fns.DataError:
            return tk.base.abort(400, tk._(u'Integrity Error'))
        except tk.NotAuthorized:
            message = tk._(u'Unauthorized to edit collaborators {}').format(id)
            return tk.base.abort(401, tk._(message))
        except tk.ObjectNotFound:
            h.flash_error(tk._('User not found'))
            return h.redirect_to(u'dataset.new_collaborator', id=id)
        except tk.ValidationError as e:
            h.flash_error(e.error_summary)
            return h.redirect_to(u'dataset.new_collaborator', id=id)
        else:
            h.flash_success(tk._(u'User added to collaborators'))

        return h.redirect_to(u'dataset.collaborators_read', id=id)

    def get(self, id: str) -> Union[Response, str]:  # noqa
        context = cast(Context, {u'model': model, u'user': g.user})
        data_dict = {u'id': id}

        try:
            logic.check_access(u'package_collaborator_list', context, data_dict)
            # needed to ckan_extend package/edit_base.html
            pkg_dict = logic.get_action(u'package_show')(context, data_dict)
        except tk.NotAuthorized:
            message = u'Unauthorized to read collaborators {}'.format(id)
            return tk.base.abort(401, tk._(message))
        except tk.ObjectNotFound:
            return tk.base.abort(404, tk._(u'Resource not found'))

        user = request.args.get(u'user_id')
        group = request.args.get(u'group_id')
        user_capacity = u'member'
        group_capacity = u'member'

        if user:
            collaborators = logic.get_action(u'package_collaborator_list')(
                context, data_dict)
            for c in collaborators:
                if c[u'user_id'] == user:
                    user_capacity = c[u'capacity']
            user = logic.get_action(u'user_show')(context, {u'id': user})

        if group:
            collaborators = logic.get_action(u'package_collaborator_list_for_group')(
                context, data_dict
            )
            for c in collaborators:
                if c[u'group_id'] == group:
                    group_capacity = c[u'capacity']
            group = logic.get_action(u'group_show')(context, {'id': group})

        capacities: list[dict[str, str]] = []
        if authz.check_config_permission(u'allow_admin_collaborators'):
            capacities.append({u'name': u'admin', u'value': u'admin'})
        capacities.extend([
            {u'name': u'editor', u'value': u'editor'},
            {u'name': u'member', u'value': u'member'}
        ])

        extra_vars: dict[str, Any] = {
            u'capacities': capacities,
            u'user_capacity': user_capacity,
            u'user': user,
            u'group_capacity': group_capacity,
            u'group': group,
            u'pkg_dict': pkg_dict,
        }

        return tk.base.render(
            u'/package/collaborators/collaborator_new.html', extra_vars)


collaborator_group.add_url_rule(
    '/dataset/collaborators/<id>/new',
    view_func=CollaboratorEditView.as_view(str(u'new_collaborator')),
    methods=[u'GET', u'POST', ]
)
collaborator_group.add_url_rule(
    rule=u'/collaborators/<id>/delete/<user_id>',
    view_func=collaborator_delete, methods=['POST', ]
)