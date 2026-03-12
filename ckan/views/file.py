from __future__ import annotations

import jwt
import logging
from typing import Any

from flask import Blueprint

from ckan import logic, model
from ckan.lib import base, files, api_token
from ckan.types import Response


log = logging.getLogger(__name__)
blueprint = Blueprint("file", __name__)


def _as_response(storage_name: str, location: str):
    """Return a response for a file stored in the given location.

    The storage is looked up by name, and the file data is created from the
    location string. This is a helper function for the all kind of download
    routes.
    """
    try:
        storage = files.get_storage(storage_name)
    except files.exc.UnknownStorageError:
        return base.abort(404)

    data = files.FileData.from_string(location)

    if isinstance(storage, files.Storage):
        return storage.as_response(data)

    return base.abort(422, "File is not downloadable")


@blueprint.route("/file/download/<id>")
def download(id: str) -> Response:
    """Download a file by its ID."""
    try:
        logic.check_access("permission_download_file", {}, {"id": id})
        item: dict[str, Any] = logic.get_action("file_show")({}, {"id": id})
    except logic.NotFound:
        return base.abort(404)
    except logic.NotAuthorized:
        return base.abort(403)

    return _as_response(item["storage"], item["location"])


@blueprint.route("/file/trusted-download/<token>")
def trusted_download(token: str) -> Response:
    try:
        data = api_token.decode_token(token)

    except jwt.ExpiredSignatureError as err:
        log.debug("Expired file-download token: %s", err)
        return base.abort(404)

    except jwt.InvalidTokenError as err:
        log.debug("Cannot decode file-download token: %s", err)
        return base.abort(404)

    if data.get("aud") != "trusted_download":
        return base.abort(404)

    if "sub" in data:
        item = model.Session.get(model.File, data["sub"])

    elif "location" in data and "storage" in data:
        item = model.Session.scalar(
            model.File.by_location(data["location"], data["storage"]),
        )

    else:
        item = None

    if not item:
        return base.abort(404)

    return _as_response(item.storage, item.location)


@blueprint.route("/file/public-download/<storage_name>/<path:location>")
def public_download(storage_name: str, location: str) -> Response:
    try:
        storage = files.get_storage(storage_name)
    except files.exc.UnknownStorageError:
        return base.abort(404)

    if not isinstance(storage, files.Storage) or not storage.settings.public:
        return base.abort(403, "Storage is not public")

    return _as_response(storage_name, location)
