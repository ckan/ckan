# encoding: utf-8

import hmac
import hashlib
from typing import Optional

import six

from ckan.common import config, request

secret: Optional[bytes] = None


def get_message_hash(value: str) -> str:
    global secret
    if not secret:
        # avoid getting config value at module scope since config may
        # not be read in yet
        secret = six.ensure_binary(config['beaker.session.secret'])
    return hmac.new(secret, value.encode('utf8'), hashlib.sha1).hexdigest()


def get_redirect() -> Optional[bytes]:
    '''Checks the return_to value against the hash, and if it
    is valid then returns the return_to for redirect. Otherwise
    it returns None.'''
    return_to = request.args.get('return_to')
    hash_given = request.args.get('hash', '')
    if not (return_to and hash_given):
        return None
    hash_expected = get_message_hash(return_to)
    if hash_given == hash_expected:
        return return_to.encode('utf-8')
    return None
