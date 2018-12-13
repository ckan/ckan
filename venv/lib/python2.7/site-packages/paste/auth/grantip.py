# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Grant roles and logins based on IP address.
"""
from paste.util import ip4

class GrantIPMiddleware(object):

    """
    On each request, ``ip_map`` is checked against ``REMOTE_ADDR``
    and logins and roles are assigned based on that.

    ``ip_map`` is a map of {ip_mask: (username, roles)}.  Either
    ``username`` or ``roles`` may be None.  Roles may also be prefixed
    with ``-``, like ``'-system'`` meaning that role should be
    revoked.  ``'__remove__'`` for a username will remove the username.

    If ``clobber_username`` is true (default) then any user
    specification will override the current value of ``REMOTE_USER``.
    ``'__remove__'`` will always clobber the username.

    ``ip_mask`` is something that `paste.util.ip4:IP4Range
    <class-paste.util.ip4.IP4Range.html>`_ can parse.  Simple IP
    addresses, IP/mask, ip<->ip ranges, and hostnames are allowed.
    """

    def __init__(self, app, ip_map, clobber_username=True):
        self.app = app
        self.ip_map = []
        for key, value in ip_map.items():
            self.ip_map.append((ip4.IP4Range(key),
                                self._convert_user_role(value[0], value[1])))
        self.clobber_username = clobber_username

    def _convert_user_role(self, username, roles):
        if roles and isinstance(roles, basestring):
            roles = roles.split(',')
        return (username, roles)
        
    def __call__(self, environ, start_response):
        addr = ip4.ip2int(environ['REMOTE_ADDR'], False)
        remove_user = False
        add_roles = []
        for range, (username, roles) in self.ip_map:
            if addr in range:
                if roles:
                    add_roles.extend(roles)
                if username == '__remove__':
                    remove_user = True
                elif username:
                    if (not environ.get('REMOTE_USER')
                        or self.clobber_username):
                        environ['REMOTE_USER'] = username
        if (remove_user and 'REMOTE_USER' in environ):
            del environ['REMOTE_USER']
        if roles:
            self._set_roles(environ, add_roles)
        return self.app(environ, start_response)

    def _set_roles(self, environ, roles):
        cur_roles = environ.get('REMOTE_USER_TOKENS', '').split(',')
        # Get rid of empty roles:
        cur_roles = filter(None, cur_roles)
        remove_roles = []
        for role in roles:
            if role.startswith('-'):
                remove_roles.append(role[1:])
            else:
                if role not in cur_roles:
                    cur_roles.append(role)
        for role in remove_roles:
            if role in cur_roles:
                cur_roles.remove(role)
        environ['REMOTE_USER_TOKENS'] = ','.join(cur_roles)
        
                
def make_grantip(app, global_conf, clobber_username=False, **kw):
    """
    Grant roles or usernames based on IP addresses.

    Config looks like this::

      [filter:grant]
      use = egg:Paste#grantip
      clobber_username = true
      # Give localhost system role (no username):
      127.0.0.1 = -:system
      # Give everyone in 192.168.0.* editor role:
      192.168.0.0/24 = -:editor
      # Give one IP the username joe:
      192.168.0.7 = joe
      # And one IP is should not be logged in:
      192.168.0.10 = __remove__:-editor
      
    """
    from paste.deploy.converters import asbool
    clobber_username = asbool(clobber_username)
    ip_map = {}
    for key, value in kw.items():
        if ':' in value:
            username, role = value.split(':', 1)
        else:
            username = value
            role = ''
        if username == '-':
            username = ''
        if role == '-':
            role = ''
        ip_map[key] = value
    return GrantIPMiddleware(app, ip_map, clobber_username)
    
    
