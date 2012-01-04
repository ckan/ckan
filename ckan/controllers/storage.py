import re
import urllib
import uuid
from datetime import datetime
from cgi import FieldStorage

from ofs import get_impl
from pylons import request, response
from pylons.controllers.util import abort, redirect_to
from pylons import config
from paste.fileapp import FileApp

from ckan.lib.base import BaseController, c, request, render, config, h, abort
from ckan.lib.jsonp import jsonpify
import ckan.model as model
import ckan.authz as authz


try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
try:
    import json
except:
    import simplejson as json

from logging import getLogger
log = getLogger(__name__)


# pairtree_version0_1 file for identifying folders
BUCKET = config['storage.bucket']
key_prefix = config.get('storage.key_prefix', 'file/')


_eq_re = re.compile(r"^(.*)(=[0-9]*)$")
def fix_stupid_pylons_encoding(data):
    """
    Fix an apparent encoding problem when calling request.body
    TODO: Investigate whether this is fixed in later versions?
    """
    if data.startswith("%") or data.startswith("+"):
        data = urllib.unquote_plus(data)
    m = _eq_re.match(data)
    if m:
        data = m.groups()[0]
    return data


def get_ofs():
    """
    Return a configured instance of the appropriate OFS driver, in all
    cases here this will be the local file storage so we fix the implementation
    to use pairtree.
    """
    kw = {}
    for k,v in config.items():
        if not k.startswith('ofs.'):
            continue
        kw[k[4:]] = v
    ofs = get_impl("pairtree")(**kw)
    return ofs


def authorize(method, bucket, key, user, ofs):
    """
    Check authz for the user with a given bucket/key combo within a 
    particular ofs implementation.
    """
    if not method in ['POST', 'GET', 'PUT', 'DELETE']:
        abort(400)
    if method != 'GET':
        # do not allow overwriting
        if ofs.exists(bucket, key):
            abort(409)
        # now check user stuff
        username = user.name if user else ''
        is_authorized = authz.Authorizer.is_authorized(username, 'file-upload', model.System()) 
        if not is_authorized:
            h.flash_error('Not authorized to upload files.')
            abort(401)



class StorageController(BaseController):
    '''Upload to storage backend.
    '''
    @property
    def ofs(self):
        return get_ofs()

    def _get_form_for_remote(self):
        # would be nice to use filename of file
        # problem is 'we' don't know this at this point and cannot add it to
        # success_action_redirect and hence cannnot display to user afterwards
        # + '/${filename}'
        label = key_prefix + request.params.get('filepath', str(uuid.uuid4()))
        method = 'POST'
        authorize(method, BUCKET, label, c.userobj, self.ofs)
        content_length_range = int(
                config.get('ckanext.storage.max_content_length',
                    50000000))
        success_action_redirect = h.url_for('storage_upload_success', qualified=True,
                bucket=BUCKET, label=label)
        acl = 'public-read'
        fields = [ {
                'name': self.ofs.conn.provider.metadata_prefix + 'uploaded-by',
                'value': c.userobj.id
                }]
        conditions = [ '{"%s": "%s"}' % (x['name'], x['value']) for x in fields ]
        c.data = self.ofs.conn.build_post_form_args(
            BUCKET,
            label,
            expires_in=3600,
            max_content_length=content_length_range,
            success_action_redirect=success_action_redirect,
            acl=acl,
            fields=fields,
            conditions=conditions
            )
        for idx,field in enumerate(c.data['fields']):
            if field['name'] == 'content-length-range':
                del c.data['fields'][idx]
        c.data_json = json.dumps(c.data, indent=2)

    def upload(self):
        label = key_prefix + request.params.get('filepath', str(uuid.uuid4()))
        c.data = {
            'action': h.url_for('storage_upload_handle'),
            'fields': [
                {
                    'name': 'key',
                    'value': label
                }
            ]
        }
        return render('storage/index.html')

    def upload_handle(self):
        bucket_id = BUCKET
        params = dict(request.params.items())
        stream = params.get('file')
        label = params.get('key')
        authorize('POST', BUCKET, label, c.userobj, self.ofs)
        if not label:
            abort(400, "No label")
        if not isinstance(stream, FieldStorage):
            abort(400, "No file stream.")
        del params['file']
        params['filename-original'] = stream.filename
        params['_owner'] = c.userobj.id if c.userobj else ""
        params['uploaded-by'] = c.userobj.id if c.userobj else ""
        
        self.ofs.put_stream(bucket_id, label, stream.file, params)
        success_action_redirect = h.url_for('storage_upload_success', qualified=True,
                bucket=BUCKET, label=label)
        # Do not redirect here as it breaks js file uploads (get infinite loop
        # in FF and crash in Chrome)

        return self.success(label)

    def success(self, label=None):
        label=request.params.get('label', label)
        h.flash_success('Upload successful')
        c.file_url = h.url_for('storage_file',
                label=label, 
                qualified=True
                )
        c.upload_url = h.url_for('storage_upload')
        
        # TODO:
        # Publish a job onto the queue for the archiver so that it can check
        # this resource and upload to somewhere else out of bounds to this 
        # request
        # from ckan.lib.celery_app import celery
        # from ckan.model.types import make_uuid
        # task_id = make_uuid()
        # context = {}
        # data = label
        # celery.send_task("archiver.upload", args=[context, data], task_id=task_id)
        
        return render('storage/success.html')

    def success_empty(self, label=None):
        # very simple method that just returns 200 OK
        return ''

    def file(self, label):
        exists = self.ofs.exists(BUCKET, label)
        if not exists:
            # handle erroneous trailing slash by redirecting to url w/o slash
            if label.endswith('/'):
                label = label[:-1]
                file_url = h.url_for(
                    'storage_file',
                    label=label
                    )
                h.redirect_to(file_url)
            else:
                abort(404)
        file_url = self.ofs.get_url(BUCKET, label)
        if file_url.startswith("file://"):
            metadata = self.ofs.get_metadata(BUCKET, label)
            filepath = file_url[len("file://"):]
            headers = {
                # 'Content-Disposition':'attachment; filename="%s"' % label,
                'Content-Type':metadata.get('_format', 'text/plain')}
            fapp = FileApp(filepath, headers=None, **headers)
            return fapp(request.environ, self.start_response)
        else:
            h.redirect_to(file_url)

