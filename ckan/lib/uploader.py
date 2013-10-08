import os
import cgi
import pylons
import datetime
import ckan.lib.munge as munge

class Upload(object):
    def __init__(self, object_type, old_filename=None):
        path = pylons.config.get('ckan.storage_path', '/tmp')
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

    def register_request(self, request, url_field, file_field, clear_field):
        self.url = request.POST.get(url_field, '')
        self.clear = request.POST.get(clear_field)
        self.upload_field_storage = request.POST.pop(file_field, None)

        if isinstance(self.upload_field_storage, cgi.FieldStorage):
            self.filename = self.upload_field_storage.filename
            self.filename = str(datetime.datetime.utcnow()) + self.filename
            self.filename = munge.munge_filename(self.filename)
            self.filepath = os.path.join(self.storage_path, self.filename)
            request.POST[url_field] = self.filename
            self.upload_file = self.upload_field_storage.file
            self.tmp_filepath = self.filepath + '~'
        ### keep the file if there has been no change
        elif self.old_filename and not self.old_filename.startswith('http'):
            if not self.clear:
                request.POST[url_field] = self.old_filename
            if self.clear and self.url == self.old_filename:
                request.POST[url_field] = ''


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
