import hashlib
import logging

from urllib.parse import unquote


from ckan.common import request
from ckan.types import Response

from ckanext.tracking.model import TrackingRaw


logger = logging.getLogger(__name__)


def track_request(response: Response) -> Response:
    path = request.environ.get('PATH_INFO')
    method = request.environ.get('REQUEST_METHOD')
    if path == '/_tracking' and method == 'POST':
        # wsgi.input is a BytesIO object
        payload = request.environ['wsgi.input'].read().decode()
        parts = payload.split('&')
        data = {}
        for part in parts:
            k, v = part.split('=')
            data[k] = unquote(v)

        # we want a unique anonomized key for each user so that we do
        # not count multiple clicks from the same user.
        key = ''.join([
            request.environ['HTTP_USER_AGENT'],
            request.environ['REMOTE_ADDR'],
            request.environ.get('HTTP_ACCEPT_LANGUAGE', ''),
            request.environ.get('HTTP_ACCEPT_ENCODING', ''),
        ])
        # raises a type error on python<3.9
        h = hashlib.new('md5', usedforsecurity=False)
        h.update(key.encode())
        key = h.hexdigest()
        # store key/data here
        try:
            logger.debug(
                "Tracking %s for %s",
                data.get('type'),
                data.get('url'),
            )
            TrackingRaw.create(
                user_key=key,
                url=data.get("url"),
                tracking_type=data.get("type")
            )
        except Exception as e:
            logger.error("Error tracking request", e)

    return response
