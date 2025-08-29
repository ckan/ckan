from __future__ import annotations

import logging
from typing import Any

from flask import Blueprint

from ckan import logic
from ckan.lib import base, files
from ckan.types import Response


log = logging.getLogger(__name__)
blueprint = Blueprint("files", __name__)


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

    storage = files.get_storage(item["storage"])
    data = files.FileData.from_dict(item)

    if isinstance(storage, files.Storage):
        return storage.as_response(data)

    return base.abort(422, "File is not downloadable")


# @blueprint.route("/file/trusted-download/<token>")
# def trusted_download(token: str) -> Response:
#     try:
#         data = decode_token(token)

#     except jwt.ExpiredSignatureError as err:
#         log.debug("Expired file-download token: %s", err)
#         return base.abort(404)

#     except jwt.InvalidTokenError as err:
#         log.debug("Cannot decode file-download token: %s", err)
#         return base.abort(404)

#     if data.get("aud") != "trusted_download":
#         return base.abort(404)

#     if "sub" in data:
#         item = model.Session.get(model.File, data["sub"])

#     elif "location" in data and "storage" in data:
#         item = model.Session.scalar(
#             model.File.by_location(data["location"], data["storage"]),
#         )

#     else:
#         item = None

#     if not item:
#         return base.abort(404)

#     storage = files.get_storage(item.storage)
#     data = files.FileData.from_object(item)

#     if isinstance(storage, files.Storage):
#         return storage.as_response(data)

#     return base.abort(422, "File is not downloadable")
