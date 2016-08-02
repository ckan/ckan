# encoding: utf-8

import hmac
import hashlib

from ckan.common import config, request

secret = None

def get_message_hash(value):
    global secret
    if not secret:
        # avoid getting config value at module scope since config may
        # not be read in yet
        secret = config['beaker.session.secret']
    return hmac.new(secret, value.encode('utf8'), hashlib.sha1).hexdigest()

def get_redirect():
    '''Checks the return_to value against the hash, and if it
    is valid then returns the return_to for redirect. Otherwise
    it returns None.'''
    return_to = request.params.get('return_to')
    hash_given = request.params.get('hash', '')
    if not (return_to and hash_given):
        return None
    hash_expected = get_message_hash(return_to)
    if hash_given == hash_expected:
        return return_to.encode('utf-8')
    return None
