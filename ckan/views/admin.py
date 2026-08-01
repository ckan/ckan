from __future__ import annotations

import datetime
import logging
from typing import Any

from flask import Blueprint
from flask.views import MethodView
from flask.wrappers import Response
from rq.exceptions import NoSuchJobError
from rq.job import Job
from rq.registry import FailedJobRegistry, FinishedJobRegistry, StartedJobRegistry

import ckan.lib.navl.dictization_functions as dict_fns
import ckan.logic.schema
from ckan import logic, model
from ckan.common import _, config, current_user, request
from ckan.lib import app_globals, base, jobs
from ckan.lib.helpers import helper_functions as h
from ckan.lib.pagination import Page
from ckan.types import Context, Query
from ckan.views.home import CACHE_PARAMETERS

PURGE_BATCH_SIZE = 100
PURGE_JOBS_SHOWN = 15


TRASH_PURGE_ACTIONS = {
    "dataset": "dataset_purge",
    "group": "group_purge",
    "organization": "organization_purge",
}

TRASH_RESTORE_ACTIONS = {
    "dataset": "package_patch",
    "group": "group_patch",
    "organization": "organization_patch",
}


log = logging.getLogger(__name__)

admin = Blueprint("admin", __name__, url_prefix="/ckan-admin")


def _purge_queue_name() -> str:
    return config["ckan.admin.trash_purge_queue"]


def _get_sysadmins() -> Query[model.User]:
    return model.Session.query(model.User).filter(
        model.User.sysadmin.is_(True), model.User.state == model.State.ACTIVE
    )


def _get_config_items() -> list[str]:
    return [
        "ckan.site_title",
        "ckan.theme",
        "ckan.site_description",
        "ckan.site_logo",
        "ckan.site_about",
        "ckan.site_intro_text",
        "ckan.site_custom_css",
    ]


@admin.before_request
def before_request() -> None:
    try:
        context: Context = {"user": current_user.name, "auth_user_obj": current_user}
        logic.check_access("sysadmin", context)
    except logic.NotAuthorized:
        base.abort(403, _("Need to be system administrator to administer"))


def index() -> str:
    return base.render(
        "admin/index.html", extra_vars={"sysadmins": [a.name for a in _get_sysadmins()]}
    )


class ResetConfigView(MethodView):
    def get(self) -> str | Response:
        if "cancel" in request.args:
            return h.redirect_to("admin.config")
        return base.render("admin/confirm_reset.html", extra_vars={})

    def post(self) -> Response:
        # remove sys info items
        for item in _get_config_items():
            model.delete_system_info(item)
        # reset to values in config
        app_globals.reset()
        return h.redirect_to("admin.config")


class ConfigView(MethodView):
    def get(self) -> str:
        schema = ckan.logic.schema.update_configuration_schema()
        data = {}
        for key in schema:
            data[key] = config.get(key)

        vars = {"data": data, "errors": {}}

        return base.render("admin/config.html", extra_vars=vars)

    def post(self) -> str | Response:
        try:
            req: dict[str, Any] = request.form.copy()
            req.update(request.files.to_dict())
            data_dict = logic.clean_dict(
                dict_fns.unflatten(
                    logic.tuplize_dict(
                        logic.parse_params(req, ignore_keys=CACHE_PARAMETERS)
                    )
                )
            )

            del data_dict["save"]
            data = logic.get_action("config_option_update")(
                {"user": current_user.name}, data_dict
            )

        except logic.ValidationError as e:
            data = request.form
            errors = e.error_dict
            error_summary = e.error_summary
            vars = {"data": data, "errors": errors, "error_summary": error_summary}
            return base.render("admin/config.html", extra_vars=vars)

        return h.redirect_to("admin.config")


def _dictize_deleted_entity(entity: Any) -> dict[str, Any]:
    """Dictize a deleted entity.

    Normalize a deleted Package/Group model instance or a
    package_search result dict into the shape the trash templates need.
    """
    if isinstance(entity, dict):
        return {
            "id": entity["id"],
            "name": entity.get("name"),
            "title": entity.get("title") or entity.get("name"),
            "metadata_created": entity.get("metadata_created"),
        }
    return {
        "id": entity.id,
        "name": entity.name,
        "title": getattr(entity, "title", None) or entity.name,
        "metadata_created": getattr(entity, "metadata_created", None)
        or getattr(entity, "created", None),
    }


def _deleted_datasets_query() -> Query[model.Package]:
    return model.Session.query(model.Package).filter_by(state=model.State.DELETED)


def _deleted_groups_query(is_organization: bool) -> Query[model.Group]:
    return model.Session.query(model.Group).filter_by(
        state=model.State.DELETED, is_organization=is_organization
    )


def _deleted_datasets_page(
    limit: int, offset: int, q: str = ""
) -> tuple[list[Any], int]:
    if config.get("ckan.search.remove_deleted_packages"):
        query = _deleted_datasets_query()
        if q:
            like = f"%{q}%"
            query = query.filter(
                model.Package.name.ilike(like) | model.Package.title.ilike(like)
            )
        return query.offset(offset).limit(limit).all(), query.count()

    package_search = logic.get_action("package_search")
    search_params: dict[str, Any] = {
        "fq": "+state:deleted",
        "include_private": True,
        "start": offset,
        "rows": limit,
    }
    if q:
        search_params["q"] = q
    results = package_search({"ignore_auth": True}, search_params)
    return results["results"], results["count"]


def _deleted_entities_page(
    ent_type: str, limit: int, offset: int, q: str = ""
) -> tuple[list[Any], int]:
    if ent_type == "dataset":
        entities, total = _deleted_datasets_page(limit, offset, q)
    else:
        query = _deleted_groups_query(is_organization=ent_type == "organization")
        if q:
            like = f"%{q}%"
            query = query.filter(
                model.Group.name.ilike(like) | model.Group.title.ilike(like)
            )
        entities, total = query.offset(offset).limit(limit).all(), query.count()

    return [_dictize_deleted_entity(e) for e in entities], total


def _all_deleted_ids(ent_type: str) -> list[str]:
    if ent_type == "dataset":
        return [p.id for p in _deleted_datasets_query()]
    query = _deleted_groups_query(is_organization=ent_type == "organization")
    return [g.id for g in query]


def purge_entities_job(ent_type: str, ids: list[str] | None = None) -> None:
    """Background job: purge deleted entities of the given type.

    If ``ids`` is ``None`` all currently-deleted entities of that type are
    purged, re-queried at run time so a slow-to-start job doesn't purge a
    stale id list.
    """
    action = TRASH_PURGE_ACTIONS[ent_type]
    if ids is None:
        ids = _all_deleted_ids(ent_type)

    purged = 0
    for entity_id in ids:
        try:
            logic.get_action(action)({"ignore_auth": True}, {"id": entity_id})
            purged += 1
        except logic.NotFound:
            # This entity was already purged or never existed
            log.debug("Failed to purge %s %s", ent_type, entity_id)
        except logic.ValidationError:
            log.exception("Failed to purge %s %s", ent_type, entity_id)

        if purged % PURGE_BATCH_SIZE == 0:
            model.Session.remove()

    model.Session.remove()
    log.info("Purged %s/%s deleted %s(s)", purged, len(ids), ent_type)


PURGE_JOB_FUNC_NAME = (
    f"{purge_entities_job.__module__}.{purge_entities_job.__qualname__}"
)


def _purge_job_statuses() -> list[dict[str, Any]]:
    """Purge job statuses.

    Recent purge jobs (queued/started/finished/failed) for the status
    panel, newest first. Reads RQ's registries directly since the
    ``job_list``/``job_show`` actions only ever see still-queued jobs.
    """
    queue = jobs.get_queue(_purge_queue_name())
    conn = queue.connection

    job_ids = set(queue.job_ids)
    job_ids.update(StartedJobRegistry(queue=queue).get_job_ids())
    job_ids.update(FinishedJobRegistry(queue=queue).get_job_ids())
    job_ids.update(FailedJobRegistry(queue=queue).get_job_ids())

    statuses = []
    for job_id in job_ids:
        try:
            job = Job.fetch(job_id, connection=conn)
        except NoSuchJobError:
            continue

        if job.func_name != PURGE_JOB_FUNC_NAME:
            continue

        status = job.get_status(refresh=False)
        statuses.append(
            {
                "id": job.id,
                "title": (job.meta or {}).get("title") or job.id,
                "status": getattr(status, "value", status),
                "created": job.created_at,
                "ended": job.ended_at,
            }
        )

    epoch = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)  # noqa: UP017
    statuses.sort(key=lambda j: j["created"] or epoch, reverse=True)
    return statuses[:PURGE_JOBS_SHOWN]


class TrashView(MethodView):
    def get(self, ent_type: str = "dataset") -> str | Response:
        if ent_type not in TRASH_PURGE_ACTIONS:
            return base.abort(404, _("Unknown entity type"))

        q = request.args.get("q", "").strip()
        per_page = config.get("ckan.datasets_per_page")
        page_number = h.get_page_number(request.args)
        offset = (page_number - 1) * per_page

        entities, total = _deleted_entities_page(ent_type, per_page, offset, q)

        page = Page(
            collection=entities,
            page=page_number,
            presliced_list=True,
            url=h.pager_url,
            item_count=total,
            items_per_page=per_page,
        )

        data = {
            "ent_type": ent_type,
            "page": page,
            "q": q,
            "purge_jobs": _purge_job_statuses(),
        }
        return base.render("admin/trash.html", extra_vars=data)

    def post(self, ent_type: str = "dataset") -> Response:
        if ent_type not in TRASH_PURGE_ACTIONS:
            return base.abort(404, _("Unknown entity type"))

        if "cancel" in request.form:
            return h.redirect_to("admin.trash", ent_type=ent_type)

        # request.values (not request.form) so a single-row action button
        # can trigger via a query-string GET-turned-POST (see trash_table.html)
        # without needing its own nested <form>.
        req_action = request.values.get("action", "")
        if req_action == "purge_selected":
            self._purge_selected(ent_type, request.values.getlist("entity_id"))
        elif req_action == "purge_all":
            self._purge_all(ent_type)
        elif req_action == "restore_single":
            self._restore_single(ent_type, request.values.get("entity_id", ""))
        elif req_action == "restore_selected":
            self._restore_selected(ent_type, request.values.getlist("entity_id"))
        else:
            h.flash_error(_("Action not implemented."))

        return h.redirect_to("admin.trash", ent_type=ent_type)

    def _purge_single(self, ent_type: str, entity_id: str) -> None:
        try:
            logic.get_action(TRASH_PURGE_ACTIONS[ent_type])(
                {"user": current_user.name}, {"id": entity_id}
            )
            h.flash_success(_("Entity has been purged"))
        except logic.NotFound:
            h.flash_error(_("Entity not found"))
        except logic.ValidationError as e:
            h.flash_error(e.error_summary or str(e))

    def _restore_single(self, ent_type: str, entity_id: str) -> None:
        if not entity_id:
            h.flash_error(_("No entity selected"))
            return
        try:
            logic.get_action(TRASH_RESTORE_ACTIONS[ent_type])(
                {"user": current_user.name},
                {"id": entity_id, "state": model.State.ACTIVE},
            )
            h.flash_success(_("Entity has been restored"))
        except logic.NotFound:
            h.flash_error(_("Entity not found"))

    def _restore_selected(self, ent_type: str, ids: list[str]) -> None:
        ids = [i for i in ids if i]
        if not ids:
            h.flash_error(_("No entities selected"))
            return

        action = TRASH_RESTORE_ACTIONS[ent_type]
        restored = 0
        for entity_id in ids:
            try:
                logic.get_action(action)(
                    {"user": current_user.name},
                    {"id": entity_id, "state": model.State.ACTIVE},
                )
                restored += 1
            except logic.NotFound:
                log.debug("Failed to restore %s %s", ent_type, entity_id)

        h.flash_success(
            _("{number} {ent_type}(s) have been restored").format(
                number=restored, ent_type=ent_type
            )
        )

    def _purge_selected(self, ent_type: str, ids: list[str]) -> None:
        ids = [i for i in ids if i]
        if not ids:
            h.flash_error(_("No entities selected"))
            return

        if len(ids) == 1:
            self._purge_single(ent_type, ids[0])
            return

        jobs.enqueue(
            purge_entities_job,
            args=[ent_type, ids],
            title=f"Purge {len(ids)} {ent_type}(s)",
            queue=_purge_queue_name(),
        )
        h.flash_success(
            _("Purge job for {number} {ent_type}(s) has been queued").format(
                number=len(ids), ent_type=ent_type
            )
        )

    def _purge_all(self, ent_type: str) -> None:
        jobs.enqueue(
            purge_entities_job,
            args=[ent_type, None],
            title=f"Purge all deleted {ent_type}(s)",
            queue=_purge_queue_name(),
        )
        h.flash_success(
            _("Purge job for all deleted {ent_type}(s) has been queued").format(
                ent_type=ent_type
            )
        )


admin.add_url_rule("/", view_func=index, methods=["GET"], strict_slashes=False)
admin.add_url_rule("/reset_config", view_func=ResetConfigView.as_view("reset_config"))
admin.add_url_rule("/config", view_func=ConfigView.as_view("config"))
trash_view = TrashView.as_view("trash")
admin.add_url_rule("/trash", view_func=trash_view, defaults={"ent_type": "dataset"})
admin.add_url_rule("/trash/<ent_type>", view_func=trash_view)
