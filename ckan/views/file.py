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


def _as_response(storage_name: str, data: files.FileData):
    """Return a response for a file stored in the given location.

    The storage is looked up by name, and the file data is created from the
    location string. This is a helper function for the all kind of download
    routes.
    """
    try:
        storage = files.get_storage(storage_name)
    except files.exc.UnknownStorageError:
        return base.abort(404)

    if isinstance(storage, files.Storage):
        resp = storage.as_response(data)
        if resp.status_code >= 400:
            return base.abort(resp.status_code)
        return resp

    return base.abort(422, "File is not downloadable")


@blueprint.route("/file/download/<id>")
def download(id: str) -> Response:
    """Download a file by its ID.

    The file is looked up by its ID, and the storage and location are used to
    return the file content. The user must have the "permission_download_file"
    permission for the file to access it. This is the main download route for
    files tracked in DB.
    """
    try:
        logic.check_access("permission_download_file", {}, {"id": id})
        item: dict[str, Any] = logic.get_action("file_show")({}, {"id": id})
    except (logic.NotFound, logic.NotAuthorized):
        return base.abort(404)

    return _as_response(item["storage"], files.FileData.from_dict(item))


@blueprint.route("/file/trusted-download/<token>")
def trusted_download(token: str) -> Response:
    """Download a file using a JWT token.

    The file is looked up by the information in the token, which must have the
    "trusted_download" audience. The token can contain either a "sub" claim
    with the file ID, or a "location" and "storage" claim with the file
    location. This route is intended for use by internal services that need to
    access files without going through the normal permission checks, but it can
    also be used for public downloads if the token is generated with the
    appropriate information and a short expiration time. The token can be
    generated using :py:func:`ckan.lib.api_token.encode_token`.

    If the token is invalid or expired, a 404 error is returned to avoid
    leaking information about the existence of the file. If the token is valid
    but the file is not found, a 404 error is also returned. If the token is
    valid and the file is found, the file content is returned as a response,
    using the same mechanism as the normal download route.
    """
    try:
        data = api_token.decode_token(token, audience="trusted_download")

    except jwt.ExpiredSignatureError as err:
        log.debug("Expired file-download token: %s", err)
        return base.abort(404)

    except jwt.InvalidAudienceError as err:
        log.debug("Token does not have 'trusted_download' aud: %s", err)
        return base.abort(404)

    except jwt.InvalidTokenError as err:
        log.debug("Cannot decode file-download token: %s", err)
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

    return _as_response(item.storage, files.FileData.from_object(item))


@blueprint.route("/file/public-download/<storage_name>/<path:location>")
def public_download(storage_name: str, location: str) -> Response:
    """Download a public file by its storage name and location.

    The file is looked up by its storage name and location, and the content is
    returned if the storage is public. This route is intended for files that
    are not tracked in DB, but are stored in a public storage. The user does
    not need any permissions to access the file, but the storage must be
    explicitly marked as public to prevent unauthorized access to private
    files. The file content is returned as a response, using the same mechanism
    as the normal download route.

    If the storage is not found or not public, a 404 or 403 error is returned
    respectively. If the file is not found in the storage, a 404 error is
    returned.
    """
    try:
        storage = files.get_storage(storage_name)
    except files.exc.UnknownStorageError:
        return base.abort(404)

    if not isinstance(storage, files.Storage) or not storage.settings.public:
        return base.abort(403, "Storage is not public")

    location = files.Location(location)
    try:
        data = files.FileData(
            location,
            size=storage.size(location),
            content_type=storage.content_type(location),
        )
    except files.exc.MissingFileError:
        return base.abort(404)

    return _as_response(storage_name, data)
