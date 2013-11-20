import os
import cgi
import pylons
import datetime
import ckan.lib.munge as munge
import logging
import ckan.logic as logic

log = logging.getLogger(__name__)

_storage_path = None


def get_storage_path():
    '''Function to cache storage path'''
    global _storage_path

    #None means it has not been set. False means not in config.
    if _storage_path is None:
        storage_path = pylons.config.get('ckan.storage_path')
        ofs_impl = pylons.config.get('ofs.impl')
        ofs_storage_dir = pylons.config.get('ofs.storage_dir')
        if storage_path:
            _storage_path = storage_path
        elif ofs_impl == 'pairtree' and ofs_storage_dir:
            log.warn('''Please use config option ckan.storage_path instaed of
                     ofs.storage_path''')
            _storage_path = ofs_storage_dir
            return _storage_path
        elif ofs_impl:
            log.critical('''We only support local file storage form version 2.2
                         of ckan please specify ckan.storage_path in your
                         config for your uploads''')
            _storage_path = False
        else:
            log.critical('''Please specify a ckan.storage_path in your config
                         for your uploads''')
            _storage_path = False

    return _storage_path


class Upload(object):
    def __init__(self, object_type, old_filename=None):
        ''' Setup upload by creating  a subdirectory of the storage directory
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
        try:
            os.makedirs(self.storage_path)
        except OSError, e:
            ## errno 17 is file already exists
            if e.errno != 17:
                raise
        self.object_type = object_type
        self.old_filename = old_filename
        if old_filename:
            self.old_filepath = os.path.join(self.storage_path, old_filename)

    def update_data_dict(self, data_dict, url_field, file_field, clear_field):
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

        if isinstance(self.upload_field_storage, cgi.FieldStorage):
            self.filename = self.upload_field_storage.filename
            self.filename = str(datetime.datetime.utcnow()) + self.filename
            self.filename = munge.munge_filename(self.filename)
            self.filepath = os.path.join(self.storage_path, self.filename)
            data_dict[url_field] = self.filename
            self.upload_file = self.upload_field_storage.file
            self.tmp_filepath = self.filepath + '~'
        ### keep the file if there has been no change
        elif self.old_filename and not self.old_filename.startswith('http'):
            if not self.clear:
                data_dict[url_field] = self.old_filename
            if self.clear and self.url == self.old_filename:
                data_dict[url_field] = ''

    def upload(self, max_size=2):
        ''' Actually upload the file.
        This should happen just before a commit but after the data has
        been validated and flushed to the db. This is so we do not store
        anything unless the request is actually good.
        max_size is size in MB maximum of the file'''

        if self.filename:
            output_file = open(self.tmp_filepath, 'wb')
            self.upload_file.seek(0)
            current_size = 0
            while True:
                current_size = current_size + 1
                # MB chuncks
                data = self.upload_file.read(2 ** 20)
                if not data:
                    break
                output_file.write(data)
                if current_size > max_size:
                    os.remove(self.tmp_filepath)
                    raise logic.ValidationError(
                        {self.file_field: ['File upload too large']}
                    )
            output_file.close()
            os.rename(self.tmp_filepath, self.filepath)
            self.clear = True

        if (self.clear and self.old_filename
                and not self.old_filename.startswith('http')):
            try:
                os.remove(self.old_filepath)
            except OSError, e:
                pass
