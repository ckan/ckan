import hashlib
from typing import cast

from urllib.parse import unquote

import sqlalchemy as sa

from ckan.model.meta import engine
from ckan.common import request
from ckan.types import Response


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
        sql = '''INSERT INTO tracking_raw
                    (user_key, url, tracking_type)
                     VALUES (:key, :url, :type)'''
        # Check if the engine is initialized
        if engine is None:
            return response
        with cast(sa.engine.Engine, engine).begin() as conn:
            conn.execute(sa.text(sql), {
                "key": key,
                "url": data.get("url"),
                "type": data.get("type"),
            })

    return response
