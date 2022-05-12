# encoding: utf-8
from __future__ import annotations

import os
import cgi
import datetime
import logging
import magic
import mimetypes
from typing import Any, IO, Optional, Union
from urllib.parse import urlparse

from werkzeug.datastructures import FileStorage as FlaskFileStorage

import ckan.lib.munge as munge
import ckan.logic as logic
import ckan.plugins as plugins
from ckan.common import config
from ckan.types import ErrorDict, PUploader, PResourceUploader

ALLOWED_UPLOAD_TYPES = (cgi.FieldStorage, FlaskFileStorage)
MB = 1 << 20

log = logging.getLogger(__name__)


def _copy_file(input_file: IO[bytes],
               output_file: IO[bytes], max_size: int) -> None:
    input_file.seek(0)
    current_size = 0
    while True:
        current_size = current_size + 1
        # MB chunks
        data = input_file.read(MB)

        if not data:
            break
        output_file.write(data)
        if current_size > max_size:
            raise logic.ValidationError({'upload': ['File upload too large']})


def _get_underlying_file(wrapper: Union[FlaskFileStorage, cgi.FieldStorage]):
    if isinstance(wrapper, FlaskFileStorage):
        return wrapper.stream
    return wrapper.file


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
    storage_path = config.get_value('ckan.storage_path')
    if not storage_path:
        log.critical('''Please specify a ckan.storage_path in your config
                        for your uploads''')

    return storage_path


def get_max_image_size() -> int:
    return config.get_value('ckan.max_image_size')


def get_max_resource_size() -> int:
    return config.get_value('ckan.max_resource_size')


class Upload(object):
    storage_path: Optional[str]
    filename: Optional[str]
    filepath: Optional[str]
    object_type: Optional[str]
    old_filename: Optional[str]
    old_filepath: Optional[str]
    upload_file: Optional[IO[bytes]]

    def __init__(self,
                 object_type: str,
                 old_filename: Optional[str] = None) -> None:
        ''' Setup upload by creating a subdirectory of the storage directory
        of name object_type. old_filename is the name of the file in the url
        field last time'''

        self.storage_path = None
        self.filename = None
        self.filepath = None
        path = get_storage_path()
        if not path:
            return
        self.storage_path = os.path.join(path, 'storage',
                                         'uploads', object_type)
        # check if the storage directory is already created by
        # the user or third-party
        if os.path.isdir(self.storage_path):
            pass
        else:
            try:
                os.makedirs(self.storage_path)
            except OSError as e:
                # errno 17 is file already exists
                if e.errno != 17:
                    raise
        self.object_type = object_type
        self.old_filename = old_filename
        if old_filename:
            self.old_filepath = os.path.join(self.storage_path, old_filename)

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

        if not self.storage_path:
            return

        if isinstance(self.upload_field_storage, ALLOWED_UPLOAD_TYPES):
            if self.upload_field_storage.filename:
                self.filename = self.upload_field_storage.filename
                self.filename = str(datetime.datetime.utcnow()) + self.filename
                self.filename = munge.munge_filename_legacy(self.filename)
                self.filepath = os.path.join(self.storage_path, self.filename)
                data_dict[url_field] = self.filename
                self.upload_file = _get_underlying_file(
                    self.upload_field_storage)
                self.tmp_filepath = self.filepath + '~'
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

        self.verify_type()

        if self.filename:
            assert self.upload_file and self.filepath

            with open(self.tmp_filepath, 'wb+') as output_file:
                try:
                    _copy_file(self.upload_file, output_file, max_size)
                except logic.ValidationError:
                    os.remove(self.tmp_filepath)
                    raise
                finally:
                    self.upload_file.close()
            os.rename(self.tmp_filepath, self.filepath)
            self.clear = True

        if (self.clear and self.old_filename
                and not self.old_filename.startswith('http')
                and self.old_filepath):
            try:
                os.remove(self.old_filepath)
            except OSError:
                pass

    def verify_type(self):
        if not self.filename or not self.upload_file:
            return

        mimetypes = config.get_value(
            f"ckan.upload.{self.object_type}.mimetypes")
        types = config.get_value(f"ckan.upload.{self.object_type}.types")
        if not mimetypes and not types:
            return

        actual = magic.from_buffer(self.upload_file.read(1024), mime=True)
        self.upload_file.seek(0, os.SEEK_SET)
        err: ErrorDict = {
            self.file_field: [f"Unsupported upload type: {actual}"]
        }

        if mimetypes and actual not in mimetypes:
            raise logic.ValidationError(err)

        type_ = actual.split("/")[0]
        if types and type_ not in types:
            raise logic.ValidationError(err)


class ResourceUpload(object):
    mimetype: Optional[str]

    def __init__(self, resource: dict[str, Any]) -> None:
        path = get_storage_path()
        config_mimetype_guess = config.get_value('ckan.mimetype_guess')

        if not path:
            self.storage_path = None
            return
        self.storage_path = os.path.join(path, 'resources')
        try:
            os.makedirs(self.storage_path)
        except OSError as e:
            # errno 17 is file already exists
            if e.errno != 17:
                raise
        self.filename = None
        self.mimetype = None

        url = resource.get('url')

        upload_field_storage = resource.pop('upload', None)
        self.clear = resource.pop('clear_upload', None)

        if url and config_mimetype_guess == 'file_ext' and urlparse(url).path:
            self.mimetype = mimetypes.guess_type(url)[0]

        if bool(upload_field_storage) and \
                isinstance(upload_field_storage, ALLOWED_UPLOAD_TYPES):
            self.filesize = 0  # bytes

            self.filename = upload_field_storage.filename
            assert self.filename is not None
            self.filename = munge.munge_filename(self.filename)
            resource['url'] = self.filename
            resource['url_type'] = 'upload'
            resource['last_modified'] = datetime.datetime.utcnow()
            self.upload_file = _get_underlying_file(upload_field_storage)
            assert self.upload_file is not None
            self.upload_file.seek(0, os.SEEK_END)
            self.filesize = self.upload_file.tell()
            # go back to the beginning of the file buffer
            self.upload_file.seek(0, os.SEEK_SET)

            # check if the mimetype failed from guessing with the url
            if not self.mimetype and config_mimetype_guess == 'file_ext':
                self.mimetype = mimetypes.guess_type(self.filename)[0]

            if not self.mimetype and config_mimetype_guess == 'file_contents':
                try:
                    self.mimetype = magic.from_buffer(self.upload_file.read(),
                                                      mime=True)
                    self.upload_file.seek(0, os.SEEK_SET)
                except IOError:
                    # Not that important if call above fails
                    self.mimetype = None

        elif self.clear:
            resource['url_type'] = ''

    def get_directory(self, id: str) -> str:
        assert self.storage_path
        directory = os.path.join(self.storage_path,
                                 id[0:3], id[3:6])
        return directory

    def get_path(self, id: str) -> str:
        directory = self.get_directory(id)
        filepath = os.path.join(directory, id[6:])
        return filepath

    def upload(self, id: str, max_size: int = 10) -> None:
        '''Actually upload the file.

        :returns: ``'file uploaded'`` if a new file was successfully uploaded
            (whether it overwrote a previously uploaded file or not),
            ``'file deleted'`` if an existing uploaded file was deleted,
            or ``None`` if nothing changed
        :rtype: ``string`` or ``None``

        '''
        if not self.storage_path:
            return

        # Get directory and filepath on the system
        # where the file for this resource will be stored
        directory = self.get_directory(id)
        filepath = self.get_path(id)

        # If a filename has been provided (a file is being uploaded)
        # we write it to the filepath (and overwrite it if it already
        # exists). This way the uploaded file will always be stored
        # in the same location
        if self.filename:
            try:
                os.makedirs(directory)
            except OSError as e:
                # errno 17 is file already exists
                if e.errno != 17:
                    raise
            tmp_filepath = filepath + '~'
            with open(tmp_filepath, 'wb+') as output_file:
                assert self.upload_file
                try:
                    _copy_file(self.upload_file, output_file, max_size)
                except logic.ValidationError:
                    os.remove(tmp_filepath)
                    raise
                finally:
                    self.upload_file.close()
            os.rename(tmp_filepath, filepath)
            return

        # The resource form only sets self.clear (via the input clear_upload)
        # to True when an uploaded file is not replaced by another uploaded
        # file, only if it is replaced by a link to file.
        # If the uploaded file is replaced by a link, we should remove the
        # previously uploaded file to clean up the file system.
        if self.clear:
            try:
                os.remove(filepath)
            except OSError:
                pass
