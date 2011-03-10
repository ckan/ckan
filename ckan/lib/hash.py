import hmac
import hashlib

from pylons import config

secret = config['beaker.session.secret']

def get_message_hash(value):
    return hmac.new(secret, value, hashlib.sha1).hexdigest()
