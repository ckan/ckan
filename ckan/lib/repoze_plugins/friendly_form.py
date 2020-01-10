# -*- coding: utf-8 -*-

#
# This is a modified version of repoze.who-friendlyform, written by
# Gustavo Narea <me@gustavonarea.net>
#
# Modifications include:
# * Python 3 support
# * Replace usage of paster methods with webob ones
#

##############################################################################
#
# Copyright (c) 2009-2010, Gustavo Narea <me@gustavonarea.net> and
# contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the BSD-like license at
# http://www.repoze.org/LICENSE.txt.  A copy of the license should accompany
# this distribution.  THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL
# EXPRESS OR IMPLIED WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND
# FITNESS FOR A PARTICULAR PURPOSE.
#
##############################################################################

u'''Collection of :mod:`repoze.who` friendly forms'''

from six.moves.urllib.parse import urlparse, urlunparse, urlencode, parse_qs

from webob import Request
try:
    from webob.multidict import MultiDict
except ImportError:
    from webob import UnicodeMultiDict as MultiDict

from webob.exc import HTTPFound, HTTPUnauthorized
from zope.interface import implementer

from repoze.who.interfaces import IChallenger, IIdentifier

__all__ = [u'FriendlyFormPlugin']


def construct_url(environ):
    return Request(environ).url


@implementer(IChallenger, IIdentifier)
class FriendlyFormPlugin(object):
    u'''
    :class:`RedirectingFormPlugin
    <repoze.who.plugins.form.RedirectingFormPlugin>`-like form plugin with
    more features.

    It is like ``RedirectingFormPlugin``, but provides us with the following
    features:

    * Users are not challenged on logout, unless the referrer URL is a
      private one (but that's up to the application).
    * Developers may define post-login and/or post-logout pages.
    * In the login URL, the amount of failed logins is available in the
      environ. It's also increased by one on every login try. This counter
      will allow developers not using a post-login page to handle logins that
      fail/succeed.

    You should keep in mind that if you're using a post-login or a post-logout
    page, that page will receive the referrer URL as a query string variable
    whose name is 'came_from'.

    Forms can be submitted with any encoding (non-ASCII credentials are
    supported) and ISO-8859-1 (aka 'Latin-1') is the default one.

    '''

    classifications = {
        IIdentifier: [u'browser'],
        IChallenger: [u'browser'],
    }

    def __init__(self, login_form_url, login_handler_path, post_login_url,
                 logout_handler_path, post_logout_url, rememberer_name,
                 login_counter_name=None, charset=u'iso-8859-1'):
        u'''

        :param login_form_url: The URL/path where the login form is located.
        :type login_form_url: str
        :param login_handler_path: The URL/path where the login form is
            submitted to (where it is processed by this plugin).
        :type login_handler_path: str
        :param post_login_url: The URL/path where the user should be redirected
            to after login (even if wrong credentials were provided).
        :type post_login_url: str
        :param logout_handler_path: The URL/path where the user is logged out.
        :type logout_handler_path: str
        :param post_logout_url: The URL/path where the user should be
            redirected to after logout.
        :type post_logout_url: str
        :param rememberer_name: The name of the repoze.who identifier which
            acts as rememberer.
        :type rememberer_name: str
        :param login_counter_name: The name of the query string variable which
            will represent the login counter.
        :type login_counter_name: str
        :param charset: The character encoding to be assumed when the user
            agent does not submit the form with an explicit charset.
        :type charset: :class:`str`

        The login counter variable's name will be set to ``__logins`` if
        ``login_counter_name`` equals None.

        .. versionchanged:: 1.0.1
            Added the ``charset`` argument.

        '''
        self.login_form_url = login_form_url
        self.login_handler_path = login_handler_path
        self.post_login_url = post_login_url
        self.logout_handler_path = logout_handler_path
        self.post_logout_url = post_logout_url
        self.rememberer_name = rememberer_name
        self.login_counter_name = login_counter_name
        if not login_counter_name:
            self.login_counter_name = u'__logins'
        self.charset = charset

    # IIdentifier
    def identify(self, environ):
        u'''
        Override the parent's identifier to introduce a login counter
        (possibly along with a post-login page) and load the login counter into
        the ``environ``.

        '''
        request = Request(environ, charset=self.charset)

        path_info = environ[u'PATH_INFO']
        script_name = environ.get(u'SCRIPT_NAME') or u'/'
        query = request.GET

        if path_info == self.login_handler_path:
            # We are on the URL where repoze.who processes authentication. #
            # Let's append the login counter to the query string of the
            # 'came_from' URL. It will be used by the challenge below if
            # authorization is denied for this request.
            form = dict(request.POST)
            form.update(query)
            try:
                login = form[u'login']
                password = form[u'password']
            except KeyError:
                credentials = None
            else:
                if request.charset == u'us-ascii':
                    credentials = {
                        u'login': str(login),
                        u'password': str(password),
                    }
                else:
                    credentials = {u'login': login, u'password': password}

            try:
                credentials[u'max_age'] = form[u'remember']
            except KeyError:
                pass

            referer = environ.get(u'HTTP_REFERER', script_name)
            destination = form.get(u'came_from', referer)

            if self.post_login_url:
                # There's a post-login page, so we have to replace the
                # destination with it.
                destination = self._get_full_path(self.post_login_url,
                                                  environ)
                if u'came_from' in query:
                    # There's a referrer URL defined, so we have to pass it to
                    # the post-login page as a GET variable.
                    destination = self._insert_qs_variable(destination,
                                                           u'came_from',
                                                           query[u'came_from'])
            failed_logins = self._get_logins(environ, True)
            new_dest = self._set_logins_in_url(destination, failed_logins)
            environ[u'repoze.who.application'] = HTTPFound(location=new_dest)
            return credentials

        elif path_info == self.logout_handler_path:
            #    We are on the URL where repoze.who logs the user out.    #
            r = Request(environ)
            params = dict(list(r.GET.items()) + list(r.POST.items()))
            form = MultiDict(params)
            form.update(query)
            referer = environ.get(u'HTTP_REFERER', script_name)
            came_from = form.get(u'came_from', referer)
            # set in environ for self.challenge() to find later
            environ[u'came_from'] = came_from
            environ[u'repoze.who.application'] = HTTPUnauthorized()
            return None

        elif path_info == self.login_form_url or self._get_logins(environ):
            #  We are on the URL that displays the from OR any other page  #
            #   where the login counter is included in the query string.   #
            # So let's load the counter into the environ and then hide it from
            # the query string (it will cause problems in frameworks like TG2,
            # where this unexpected variable would be passed to the controller)
            environ[u'repoze.who.logins'] = self._get_logins(environ, True)
            # Hiding the GET variable in the environ:
            if self.login_counter_name in query:
                del query[self.login_counter_name]
                environ[u'QUERY_STRING'] = urlencode(query, doseq=True)

    # IChallenger
    def challenge(self, environ, status, app_headers, forget_headers):
        u'''
        Override the parent's challenge to avoid challenging the user on
        logout, introduce a post-logout page and/or pass the login counter
        to the login form.

        '''
        url_parts = list(urlparse(self.login_form_url))
        query = url_parts[4]
        query_elements = parse_qs(query)
        came_from = environ.get(u'came_from', construct_url(environ))
        query_elements[u'came_from'] = came_from
        url_parts[4] = urlencode(query_elements, doseq=True)
        login_form_url = urlunparse(url_parts)
        login_form_url = self._get_full_path(login_form_url, environ)
        destination = login_form_url
        # Configuring the headers to be set:
        cookies = [
            (h, v) for (h, v) in app_headers if h.lower() == u'set-cookie'
        ]
        headers = forget_headers + cookies

        if environ[u'PATH_INFO'] == self.logout_handler_path:
            # Let's log the user out without challenging.
            came_from = environ.get(u'came_from')
            if self.post_logout_url:
                # Redirect to a predefined u'post logout' URL.
                destination = self._get_full_path(self.post_logout_url,
                                                  environ)
                if came_from:
                    destination = self._insert_qs_variable(
                        destination, u'came_from', came_from)
            else:
                # Redirect to the referrer URL.
                script_name = environ.get(u'SCRIPT_NAME', u'')
                destination = came_from or script_name or u'/'

        elif u'repoze.who.logins' in environ:
            # Login failed! Let's redirect to the login form and include
            # the login counter in the query string
            environ[u'repoze.who.logins'] += 1
            # Re-building the URL:
            destination = self._set_logins_in_url(
                destination, environ[u'repoze.who.logins'])

        return HTTPFound(location=destination, headers=headers)

    # IIdentifier
    def remember(self, environ, identity):
        rememberer = self._get_rememberer(environ)
        return rememberer.remember(environ, identity)

    # IIdentifier
    def forget(self, environ, identity):
        rememberer = self._get_rememberer(environ)
        return rememberer.forget(environ, identity)

    def _get_rememberer(self, environ):
        rememberer = environ[u'repoze.who.plugins'][self.rememberer_name]
        return rememberer

    def _get_full_path(self, path, environ):
        u'''
        Return the full path to ``path`` by prepending the SCRIPT_NAME.

        If ``path`` is a URL, do nothing.

        '''
        if path.startswith(u'/'):
            path = environ.get(u'SCRIPT_NAME', u'') + path
        return path

    def _get_logins(self, environ, force_typecast=False):
        u'''
        Return the login counter from the query string in the ``environ``.

        If it's not possible to convert it into an integer and
        ``force_typecast`` is ``True``, it will be set to zero (int(0)).
        Otherwise, it will be ``None`` or an string.

        '''
        try:
            # Webob 1.0.8 (py2)
            variables = Request(environ).queryvars
        except AttributeError:
            # Webob 1.8.5 (py3)
            variables = Request(environ).params

        failed_logins = variables.get(self.login_counter_name)
        if force_typecast:
            try:
                failed_logins = int(failed_logins)
            except (ValueError, TypeError):
                failed_logins = 0
        return failed_logins

    def _set_logins_in_url(self, url, logins):
        u'''
        Insert the login counter variable with the ``logins`` value into
        ``url`` and return the new URL.

        '''
        return self._insert_qs_variable(url, self.login_counter_name, logins)

    def _insert_qs_variable(self, url, var_name, var_value):
        u'''
        Insert the variable ``var_name`` with value ``var_value`` in the query
        string of ``url`` and return the new URL.

        '''
        url_parts = list(urlparse(url))
        query_parts = parse_qs(url_parts[4])
        query_parts[var_name] = var_value
        url_parts[4] = urlencode(query_parts, doseq=True)
        return urlunparse(url_parts)

    def __repr__(self):
        return u'<%s %s>' % (self.__class__.__name__, id(self))
