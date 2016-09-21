# encoding: utf-8

from ckan.common import config

import urllib
import urllib2
import json

def check_recaptcha(request):
    '''Check a user\'s recaptcha submission is valid, and raise CaptchaError
    on failure.'''
    recaptcha_private_key = config.get('ckan.recaptcha.privatekey', '')
    if not recaptcha_private_key:
        # Recaptcha not enabled
        return
    
    client_ip_address = request.environ.get('REMOTE_ADDR', 'Unknown IP Address')
    
    recaptcha_version = config.get('ckan.recaptcha.version', '1')
    if recaptcha_version is '1':
        recaptcha_response_field = request.params.get('recaptcha_response_field', '')
        recaptcha_server_name = 'http://api-verify.recaptcha.net/verify'
        recaptcha_challenge_field = request.params.get('recaptcha_challenge_field')

        # recaptcha_response_field will be unicode if there are foreign chars in
        # the user input. So we need to encode it as utf8 before urlencoding or
        # we get an exception (#1431).
        params = urllib.urlencode(dict(privatekey=recaptcha_private_key,
                                       remoteip=client_ip_address,
                                       challenge=recaptcha_challenge_field,
                                       response=recaptcha_response_field.encode('utf8')))
        f = urllib2.urlopen(recaptcha_server_name, params)
        data = f.read()
        f.close()
        
        if not data.lower().startswith('true'):
            raise CaptchaError()
    elif recaptcha_version is '2':
        recaptcha_response_field = request.params.get('g-recaptcha-response', '')
        recaptcha_server_name = 'https://www.google.com/recaptcha/api/siteverify'

        # recaptcha_response_field will be unicode if there are foreign chars in
        # the user input. So we need to encode it as utf8 before urlencoding or
        # we get an exception (#1431).
        params = urllib.urlencode(dict(secret=recaptcha_private_key,
                                       remoteip=client_ip_address,
                                       response=recaptcha_response_field.encode('utf8')))
        f = urllib2.urlopen(recaptcha_server_name, params)
        data = json.load(f)   
        f.close()
    
        try:
            if not data['success']:
                raise CaptchaError()
        except IndexError:
            # Something weird with recaptcha response
            raise CaptchaError()

class CaptchaError(ValueError):
    pass