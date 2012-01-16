from webob import Request, Response

import openid
from openid.store import memstore, filestore, sqlstore
from openid.consumer import consumer
from openid.oidutil import appendArgs
from openid.cryptutil import randomString
from openid.fetchers import setDefaultFetcher, Urllib2Fetcher
from openid.extensions import pape, sreg, ax

# #1659 fix - logged_out_url prefixed with mount point
def get_full_path(path, environ):
    if path.startswith('/'):
        path = environ.get('SCRIPT_NAME', '') + path
    return path

def identify(self, environ):
    """this method is called when a request is incoming.

    After the challenge has been called we might get here a response
    from an openid provider.

    """

    request = Request(environ)
    # #1659 fix - Use PATH_INFO rather than request.path as the former
    #             strips off the mount point.
    path = environ['PATH_INFO']

    # first test for logout as we then don't need the rest
    if path == self.logout_handler_path:
        res = Response()
        # set forget headers
        for a,v in self.forget(environ,{}):
            res.headers.add(a,v)
        res.status = 302

        res.location = get_full_path(self.logged_out_url, environ)
        
        environ['repoze.who.application'] = res
        return {}

    identity = {}

    # first we check we are actually on the URL which is supposed to be the
    # url to return to (login_handler_path in configuration)
    # this URL is used for both: the answer for the login form and
    # when the openid provider redirects the user back.
    if path == self.login_handler_path:

    # in the case we are coming from the login form we should have 
    # an openid in here the user entered
        open_id = request.params.get(self.openid_field, None)
        if environ['repoze.who.logger'] is not None:
            environ['repoze.who.logger'].debug('checking openid results for : %s ' %open_id)

        if open_id is not None:
            open_id = open_id.strip()

        # we don't do anything with the openid we found ourselves but we put it in here
        # to tell the challenge plugin to initiate the challenge
        identity['repoze.whoplugins.openid.openid'] = environ['repoze.whoplugins.openid.openid'] = open_id

        # this part now is for the case when the openid provider redirects
        # the user back. We should find some openid specific fields in the request.
        mode=request.params.get("openid.mode", None)
        if mode=="id_res":
            oidconsumer = self.get_consumer(environ)
            info = oidconsumer.complete(request.params, request.url)
            if info.status == consumer.SUCCESS:

                fr = ax.FetchResponse.fromSuccessResponse(info)
                if fr is not None:
                    items = chain(self.ax_require.items(), self.ax_optional.items())
                    for key, value in items:
                        try:
                            identity['repoze.who.plugins.openid.' + key] = fr.get(value)
                        except KeyError:
                            pass

                fr = sreg.SRegResponse.fromSuccessResponse(info)
                if fr is not None:
                    items = chain(self.sreg_require, self.sreg_optional)
                    for key in items:
                        try:
                            identity['repoze.who.plugins.openid.' + key] = fr.get(key)
                        except KeyError:
                            pass

                environ['repoze.who.logger'].info('openid request successful for : %s ' %open_id)

                display_identifier = info.identity_url

                # remove this so that the challenger is not triggered again
                del environ['repoze.whoplugins.openid.openid']

                # store the id for the authenticator
                identity['repoze.who.plugins.openid.userid'] = display_identifier

                # now redirect to came_from or the success page
                self.redirect_to_logged_in(environ)
                return identity

            # TODO: Do we have to check for more failures and such?
            # 
        elif mode=="cancel":
            # cancel is a negative assertion in the OpenID protocol,
            # which means the user did not authorize correctly.
            environ['repoze.whoplugins.openid.error'] = 'OpenID authentication failed.'
            pass
    return identity

def redirect_to_logged_in(self, environ):
    """redirect to came_from or standard page if login was successful"""
    request = Request(environ)
    came_from = request.params.get(self.came_from_field,'')
    if came_from!='':
        url = came_from
    else:
        url = get_full_path(self.logged_in_url, environ)
    res = Response()
    res.status = 302
    res.location = url
    environ['repoze.who.application'] = res    
