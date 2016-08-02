# encoding: utf-8

'''

Note: This is the old file store controller for CKAN < 2.2.
If you are looking for how the file uploads work, you should check
`lib/uploader.py` and the `resource_download` method of the package
controller.

'''
import os
import re

from ofs import get_impl
from paste.fileapp import FileApp

from ckan.lib.base import BaseController, request, config, h, abort


from logging import getLogger
log = getLogger(__name__)


BUCKET = config.get('ckan.storage.bucket', 'default')
key_prefix = config.get('ckan.storage.key_prefix', 'file/')

_eq_re = re.compile(r"^(.*)(=[0-9]*)$")


def create_pairtree_marker(folder):
    """ Creates the pairtree marker for tests if it doesn't exist """
    if not folder[:-1] == '/':
        folder = folder + '/'

    directory = os.path.dirname(folder)
    if not os.path.exists(directory):
        os.makedirs(directory)

    target = os.path.join(directory, 'pairtree_version0_1')
    if os.path.exists(target):
        return

    open(target, 'wb').close()


def get_ofs():
    """Return a configured instance of the appropriate OFS driver.
    """
    storage_backend = config['ofs.impl']
    kw = {}
    for k, v in config.items():
        if not k.startswith('ofs.') or k == 'ofs.impl':
            continue
        kw[k[4:]] = v

    # Make sure we have created the marker file to avoid pairtree issues
    if storage_backend == 'pairtree' and 'storage_dir' in kw:
        create_pairtree_marker(kw['storage_dir'])

    ofs = get_impl(storage_backend)(**kw)
    return ofs


class StorageController(BaseController):
    '''Upload to storage backend.
    '''
    _ofs_impl = None

    @property
    def ofs(self):
        if not StorageController._ofs_impl:
            StorageController._ofs_impl = get_ofs()
        return StorageController._ofs_impl

    def file(self, label):
        exists = self.ofs.exists(BUCKET, label)
        if not exists:
            # handle erroneous trailing slash by redirecting to url w/o slash
            if label.endswith('/'):
                label = label[:-1]
                # This may be best being cached_url until we have moved it into
                # permanent storage
                file_url = h.url_for('storage_file', label=label)
                h.redirect_to(file_url)
            else:
                abort(404)

        file_url = self.ofs.get_url(BUCKET, label)
        if file_url.startswith("file://"):
            metadata = self.ofs.get_metadata(BUCKET, label)
            filepath = file_url[len("file://"):]
            headers = {
                # 'Content-Disposition':'attachment; filename="%s"' % label,
                'Content-Type': metadata.get('_format', 'text/plain')}
            fapp = FileApp(filepath, headers=None, **headers)
            return fapp(request.environ, self.start_response)
        else:
            h.redirect_to(file_url.encode('ascii', 'ignore'))
