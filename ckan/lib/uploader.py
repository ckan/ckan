import os
import cgi
import pylons
import datetime
import ckan.lib.munge as munge

class Upload(object):
    def __init__(self, object_type, old_filename=None):
        path = pylons.config.get('ckan.storage_path')
        if not path:
            return
        self.storage_path = os.path.join(path, 'storage', 'uploads', object_type)
        try:
            os.makedirs(self.storage_path)
        except OSError, e:
            pass
        self.object_type = object_type
        self.old_filename = old_filename
        if old_filename:
            self.old_filepath = os.path.join(self.storage_path, old_filename)
        self.filename = None
        self.filepath = None

    def update_data_dict(self, data_dict, url_field, file_field, clear_field):
        self.url = data_dict.get(url_field, '')
        self.clear = data_dict.pop(clear_field, None)
        self.upload_field_storage =  data_dict.pop(file_field, None)

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


    def upload(self):
        if self.filename:
            output_file = open(self.tmp_filepath, 'wb')
            self.upload_file.seek(0)
            while True:
                data = self.upload_file.read(2 ** 20) #mb chuncks
                if not data:
                    break
                output_file.write(data)
            output_file.close()
            os.rename(self.tmp_filepath, self.filepath)
            self.clear = True

        if (self.clear and self.old_filename
            and not self.old_filename.startswith('http')):
            try:
                os.remove(self.old_filepath)
            except OSError, e:
                pass


class ResourceUpload(object):
    def __init__(self, resource):
        path = pylons.config.get('ckan.storage_path')
        if not path:
            return
        self.storage_path = os.path.join(path, 'resources')
        try:
            os.makedirs(self.storage_path)
        except OSError, e:
            pass
        self.filename = None

        url = resource.get('url')
        upload_field_storage = resource.pop('upload', None)
        self.clear = resource.pop('clear_upload', None)

        if isinstance(upload_field_storage, cgi.FieldStorage):
            self.filename = upload_field_storage.filename
            self.filename = munge.munge_filename(self.filename)
            resource['url'] = self.filename
            resource['url_type'] = 'upload'
            self.upload_file = upload_field_storage.file
        elif self.clear:
            resource['url_type'] = ''


    def get_directory(self, id):
        directory = os.path.join(self.storage_path,
                                id[0:3], id[3:6])
        return directory

    def get_path(self, id):
        directory = self.get_directory(id)
        filepath = os.path.join(directory, id[6:])
        return filepath


    def upload(self, resource):
        id = resource['id']
        directory = self.get_directory(id)
        filepath = self.get_path(id)
        if self.filename:
            try:
                os.makedirs(directory)
            except OSError, e:
                pass
            tmp_filepath = filepath + '~'
            output_file = open(tmp_filepath, 'wb+')
            self.upload_file.seek(0)
            while True:
                data = self.upload_file.read(2 ** 20) #mb chuncks
                if not data:
                    break
                output_file.write(data)
            output_file.close()
            os.rename(tmp_filepath, filepath)

        if self.clear:
            try:
                os.remove(filepath)
            except OSError, e:
                pass
