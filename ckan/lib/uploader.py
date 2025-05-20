from __future__ import annotations

import contextlib
import os
import cgi
import datetime
import logging
import mimetypes
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

from werkzeug.datastructures import FileStorage as FlaskFileStorage

import ckan.lib.munge as munge
import ckan.logic as logic
import ckan.plugins as plugins
from ckan.common import config
from ckan.lib import files
from ckan.types import ErrorDict, PUploader, PResourceUploader

ALLOWED_UPLOAD_TYPES = (cgi.FieldStorage, FlaskFileStorage)
log = logging.getLogger(__name__)


def get_uploader(upload_to: str,
                 old_filename: Optional[str] = None) -> PUploader:
    '''Query IUploader plugins and return an uploader instance for general
    files.'''
    upload = None
    for plugin in plugins.PluginImplementations(plugins.IUploader):
        upload = plugin.get_uploader(upload_to, old_filename)
        if upload:
            break

    # default uploader
    if upload is None:
        upload = Upload(upload_to, old_filename)

    return upload


def get_resource_uploader(data_dict: dict[str, Any]) -> PResourceUploader:
    '''Query IUploader plugins and return a resource uploader instance.'''
    upload = None
    for plugin in plugins.PluginImplementations(plugins.IUploader):
        upload = plugin.get_resource_uploader(data_dict)
        if upload:
            break

    # default uploader
    if upload is None:
        upload = ResourceUpload(data_dict)

    return upload


def get_storage_path() -> str:
    '''Function to get the storage path from config file.'''
    storage_path = config.get('ckan.storage_path')
    if not storage_path:
        log.critical('''Please specify a ckan.storage_path in your config
                        for your uploads''')

    return storage_path


def get_max_image_size() -> int:
    return config.get('ckan.max_image_size')


def get_max_resource_size() -> int:
    return config.get('ckan.max_resource_size')


class Upload(object):
    storage: Optional[files.Storage]
    filename: Optional[str]
    object_type: Optional[str]
    old_filename: Optional[str]
    upload_file: files.Upload | None

    def __init__(self,
                 object_type: str,
                 old_filename: Optional[str] = None) -> None:
        ''' Setup upload by creating a subdirectory of the storage directory
        of name object_type. old_filename is the name of the file in the url
        field last time'''
        self.filename = None
        self.object_type = object_type
        self.old_filename = old_filename

        storage_name = f"{object_type}_uploads"
        self.storage = files.storages.get(storage_name)
        if not self.storage:
            log.debug(
                "Storage %s is not configured and upload of %s will be ignored",
                storage_name,
                object_type,
            )

    def update_data_dict(self, data_dict: dict[str, Any], url_field: str,
                         file_field: str, clear_field: str) -> None:
        ''' Manipulate data from the data_dict.  url_field is the name of the
        field where the upload is going to be. file_field is name of the key
        where the FieldStorage is kept (i.e the field where the file data
        actually is). clear_field is the name of a boolean field which
        requests the upload to be deleted.  This needs to be called before
        it reaches any validators'''

        self.url = data_dict.get(url_field, '')
        self.clear = data_dict.pop(clear_field, None)
        self.file_field = file_field
        self.upload_field_storage = data_dict.pop(file_field, None)

        if not self.storage:
            return

        if isinstance(self.upload_field_storage, ALLOWED_UPLOAD_TYPES):
            if self.upload_field_storage.filename:
                self.filename = self.upload_field_storage.filename
                self.filename = str(datetime.datetime.utcnow()) + self.filename
                self.filename = munge.munge_filename_legacy(self.filename)
                self.upload_file = files.make_upload(self.upload_field_storage)

                self.verify_type()

                data_dict[url_field] = self.filename

        # keep the file if there has been no change
        elif self.old_filename and not self.old_filename.startswith('http'):
            if not self.clear:
                data_dict[url_field] = self.old_filename
            if self.clear and self.url == self.old_filename:
                data_dict[url_field] = ''

    def upload(self, max_size: int = 2) -> None:
        ''' Actually upload the file.
        This should happen just before a commit but after the data has
        been validated and flushed to the db. This is so we do not store
        anything unless the request is actually good.
        max_size is size in MB maximum of the file'''
        if not self.storage:
            return

        if self.filename:
            assert self.upload_file

            try:
                self.storage.validate_size(self.upload_file.size)
            except files.exc.LargeUploadError as err:
                raise logic.ValidationError({"upload": [str(err)]})

            self.storage.upload(
                files.Location(self.filename),
                self.upload_file,
            )
            self.clear = True

        if (self.clear and self.old_filename
                and not self.old_filename.startswith('http')):
            with contextlib.suppress(files.exc.MissingFileError):
                self.storage.remove(files.FileData(
                    files.Location(self.old_filename)
                ))

    def verify_type(self):

        if not self.upload_file:
            return

        allowed_mimetypes = config.get(
            f"ckan.upload.{self.object_type}.mimetypes")
        allowed_types = config.get(f"ckan.upload.{self.object_type}.types")
        if not allowed_mimetypes and not allowed_types:
            raise logic.ValidationError(
                {
                    self.file_field: [
                        f"No uploads allowed for object type {self.object_type}"
                    ]
                }
            )

        # Check that the declared types in the request are supported
        declared_mimetype_from_filename = mimetypes.guess_type(
            self.upload_field_storage.filename
        )[0]
        declared_content_type = self.upload_field_storage.content_type
        for declared_mimetype in (
            declared_mimetype_from_filename,
            declared_content_type,
        ):
            if (
                declared_mimetype
                and allowed_mimetypes
                and allowed_mimetypes[0] != "*"
                and declared_mimetype not in allowed_mimetypes
            ):
                raise logic.ValidationError(
                    {
                        self.file_field: [
                            f"Unsupported upload type: {declared_mimetype}"
                        ]
                    }
                )

        # Check that the actual type guessed from the contents is supported
        # (2KB required for detecting xlsx mimetype)
        guessed_mimetype = self.upload_file.content_type

        err: ErrorDict = {
            self.file_field: [f"Unsupported upload type: {guessed_mimetype}"]
        }

        if (allowed_mimetypes
                and allowed_mimetypes[0] != "*"
                and guessed_mimetype not in allowed_mimetypes):
            raise logic.ValidationError(err)

        type_ = guessed_mimetype.split("/")[0]
        if allowed_types and allowed_types[0] != "*" and type_ not in allowed_types:
            raise logic.ValidationError(err)

        preferred_extension = mimetypes.guess_extension(guessed_mimetype)
        if preferred_extension and self.filename:
            self.filename = str(Path(self.filename).with_suffix(preferred_extension))


class ResourceUpload(object):
    mimetype: Optional[str]

    def __init__(self, resource: dict[str, Any]) -> None:
        self.storage = files.storages.get("resources")
        if not self.storage:
            log.debug("Storage resources is not configured")
            return

        config_mimetype_guess = config.get('ckan.mimetype_guess')

        self.filename = None
        self.mimetype = None

        url = resource.get('url')

        upload_field_storage = resource.pop('upload', None)
        self.clear = resource.pop('clear_upload', None)

        if url and config_mimetype_guess == 'file_ext' and urlparse(url).path:
            self.mimetype = mimetypes.guess_type(url)[0]

        if bool(upload_field_storage) and \
                isinstance(upload_field_storage, ALLOWED_UPLOAD_TYPES):

            self.upload_file = files.make_upload(upload_field_storage)
            self.filesize = self.upload_file.size
            self.filename = munge.munge_filename(self.upload_file.filename)
            resource['url'] = self.filename
            resource['url_type'] = 'upload'
            resource['last_modified'] = datetime.datetime.utcnow()

            # check if the mimetype failed from guessing with the url
            if not self.mimetype and config_mimetype_guess == 'file_ext':
                self.mimetype = mimetypes.guess_type(self.filename)[0]

            if not self.mimetype and config_mimetype_guess == 'file_contents':
                self.mimetype = self.upload_file.content_type

        elif self.clear:
            resource['url_type'] = ''

    def get_directory(self, id: str) -> str:
        if not self.storage:
            raise TypeError("storage_path is not defined")
        return os.path.join(id[0:3], id[3:6])

    def get_path(self, id: str) -> files.Location:
        directory = self.get_directory(id)
        filepath = os.path.join(directory, id[6:])

        # location is a safe version of filepath, processed with
        # transformers(e.g., converted to safe relative path)
        location = self.storage.prepare_location(filepath)  # type: ignore

        if filepath != location:
            raise logic.ValidationError({'upload': ['Invalid storage path']})

        return location

    def upload(self, id: str, max_size: int = 10) -> None:
        '''Actually upload the file.

        :returns: ``'file uploaded'`` if a new file was successfully uploaded
            (whether it overwrote a previously uploaded file or not),
            ``'file deleted'`` if an existing uploaded file was deleted,
            or ``None`` if nothing changed
        :rtype: ``string`` or ``None``

        '''
        if not self.storage:
            return

        # Get filepath on the system where the file for this resource will be
        # stored
        location = self.get_path(id)

        # If a filename has been provided (a file is being uploaded)
        # we write it to the filepath (and overwrite it if it already
        # exists). This way the uploaded file will always be stored
        # in the same location
        if self.filename:
            try:
                self.storage.validate_size(self.upload_file.size)
            except files.exc.LargeUploadError as err:
                raise logic.ValidationError({'upload': [str(err)]})

            self.storage.upload(location, self.upload_file)
            return

        # The resource form only sets self.clear (via the input clear_upload)
        # to True when an uploaded file is not replaced by another uploaded
        # file, only if it is replaced by a link to file.
        # If the uploaded file is replaced by a link, we should remove the
        # previously uploaded file to clean up the file system.
        if self.clear:
            with contextlib.suppress(files.exc.MissingFileError):
                self.storage.remove(files.FileData(location))
