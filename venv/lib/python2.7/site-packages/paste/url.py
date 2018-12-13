# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php

"""
This module implements a class for handling URLs.
"""
import urllib
import cgi
from paste import request
# Imported lazily from FormEncode:
variabledecode = None

__all__ = ["URL", "Image"]

def html_quote(v):
    if v is None:
        return ''
    return cgi.escape(str(v), 1)

def url_quote(v):
    if v is None:
        return ''
    return urllib.quote(str(v))

url_unquote = urllib.unquote

def js_repr(v):
    if v is None:
        return 'null'
    elif v is False:
        return 'false'
    elif v is True:
        return 'true'
    elif isinstance(v, list):
        return '[%s]' % ', '.join(map(js_repr, v))
    elif isinstance(v, dict):
        return '{%s}' % ', '.join(
            ['%s: %s' % (js_repr(key), js_repr(value))
             for key, value in v])
    elif isinstance(v, str):
        return repr(v)
    elif isinstance(v, unicode):
        # @@: how do you do Unicode literals in Javascript?
        return repr(v.encode('UTF-8'))
    elif isinstance(v, (float, int)):
        return repr(v)
    elif isinstance(v, long):
        return repr(v).lstrip('L')
    elif hasattr(v, '__js_repr__'):
        return v.__js_repr__()
    else:
        raise ValueError(
            "I don't know how to turn %r into a Javascript representation"
            % v)

class URLResource(object):

    """
    This is an abstract superclass for different kinds of URLs
    """

    default_params = {}

    def __init__(self, url, vars=None, attrs=None,
                 params=None):
        self.url = url or '/'
        self.vars = vars or []
        self.attrs = attrs or {}
        self.params = self.default_params.copy()
        self.original_params = params or {}
        if params:
            self.params.update(params)

    #@classmethod
    def from_environ(cls, environ, with_query_string=True,
                     with_path_info=True, script_name=None,
                     path_info=None, querystring=None):
        url = request.construct_url(
            environ, with_query_string=False,
            with_path_info=with_path_info, script_name=script_name,
            path_info=path_info)
        if with_query_string:
            if querystring is None:
                vars = request.parse_querystring(environ)
            else:
                vars = cgi.parse_qsl(
                    querystring,
                    keep_blank_values=True,
                    strict_parsing=False)
        else:
            vars = None
        v = cls(url, vars=vars)
        return v

    from_environ = classmethod(from_environ)

    def __call__(self, *args, **kw):
        res = self._add_positional(args)
        res = res._add_vars(kw)
        return res

    def __getitem__(self, item):
        if '=' in item:
            name, value = item.split('=', 1)
            return self._add_vars({url_unquote(name): url_unquote(value)})
        return self._add_positional((item,))

    def attr(self, **kw):
        for key in kw.keys():
            if key.endswith('_'):
                kw[key[:-1]] = kw[key]
                del kw[key]
        new_attrs = self.attrs.copy()
        new_attrs.update(kw)
        return self.__class__(self.url, vars=self.vars,
                              attrs=new_attrs,
                              params=self.original_params)

    def param(self, **kw):
        new_params = self.original_params.copy()
        new_params.update(kw)
        return self.__class__(self.url, vars=self.vars,
                              attrs=self.attrs,
                              params=new_params)

    def coerce_vars(self, vars):
        global variabledecode
        need_variable_encode = False
        for key, value in vars.items():
            if isinstance(value, dict):
                need_variable_encode = True
            if key.endswith('_'):
                vars[key[:-1]] = vars[key]
                del vars[key]
        if need_variable_encode:
            if variabledecode is None:
                from formencode import variabledecode
            vars = variabledecode.variable_encode(vars)
        return vars

    
    def var(self, **kw):
        kw = self.coerce_vars(kw)
        new_vars = self.vars + kw.items()
        return self.__class__(self.url, vars=new_vars,
                              attrs=self.attrs,
                              params=self.original_params)

    def setvar(self, **kw):
        """
        Like ``.var(...)``, except overwrites keys, where .var simply
        extends the keys.  Setting a variable to None here will
        effectively delete it.
        """
        kw = self.coerce_vars(kw)
        new_vars = []
        for name, values in self.vars:
            if name in kw:
                continue
            new_vars.append((name, values))
        new_vars.extend(kw.items())
        return self.__class__(self.url, vars=new_vars,
                              attrs=self.attrs,
                              params=self.original_params)

    def setvars(self, **kw):
        """
        Creates a copy of this URL, but with all the variables set/reset
        (like .setvar(), except clears past variables at the same time)
        """
        return self.__class__(self.url, vars=kw.items(),
                              attrs=self.attrs,
                              params=self.original_params)

    def addpath(self, *paths):
        u = self
        for path in paths:
            path = str(path).lstrip('/')
            new_url = u.url
            if not new_url.endswith('/'):
                new_url += '/'
            u = u.__class__(new_url+path, vars=u.vars,
                            attrs=u.attrs,
                            params=u.original_params)
        return u
            
    __div__ = addpath

    def become(self, OtherClass):
        return OtherClass(self.url, vars=self.vars,
                          attrs=self.attrs,
                          params=self.original_params)
    
    def href__get(self):
        s = self.url
        if self.vars:
            s += '?'
            vars = []
            for name, val in self.vars:
                if isinstance(val, (list, tuple)):
                    val = [v for v in val if v is not None]
                elif val is None:
                    continue
                vars.append((name, val))
            s += urllib.urlencode(vars, True)
        return s

    href = property(href__get)

    def __repr__(self):
        base = '<%s %s' % (self.__class__.__name__,
                           self.href or "''")
        if self.attrs:
            base += ' attrs(%s)' % (
                ' '.join(['%s="%s"' % (html_quote(n), html_quote(v))
                          for n, v in self.attrs.items()]))
        if self.original_params:
            base += ' params(%s)' % (
                ', '.join(['%s=%r' % (n, v)
                           for n, v in self.attrs.items()]))
        return base + '>'
    
    def html__get(self):
        if not self.params.get('tag'):
            raise ValueError(
                "You cannot get the HTML of %r until you set the "
                "'tag' param'" % self)
        content = self._get_content()
        tag = '<%s' % self.params.get('tag')
        attrs = ' '.join([
            '%s="%s"' % (html_quote(n), html_quote(v))
            for n, v in self._html_attrs()])
        if attrs:
            tag += ' ' + attrs
        tag += self._html_extra()
        if content is None:
            return tag + ' />'
        else:
            return '%s>%s</%s>' % (tag, content, self.params.get('tag'))

    html = property(html__get)

    def _html_attrs(self):
        return self.attrs.items()

    def _html_extra(self):
        return ''

    def _get_content(self):
        """
        Return the content for a tag (for self.html); return None
        for an empty tag (like ``<img />``)
        """
        raise NotImplementedError
    
    def _add_vars(self, vars):
        raise NotImplementedError

    def _add_positional(self, args):
        raise NotImplementedError

class URL(URLResource):

    r"""
    >>> u = URL('http://localhost')
    >>> u
    <URL http://localhost>
    >>> u = u['view']
    >>> str(u)
    'http://localhost/view'
    >>> u['//foo'].param(content='view').html
    '<a href="http://localhost/view/foo">view</a>'
    >>> u.param(confirm='Really?', content='goto').html
    '<a href="http://localhost/view" onclick="return confirm(\'Really?\')">goto</a>'
    >>> u(title='See "it"', content='goto').html
    '<a href="http://localhost/view?title=See+%22it%22">goto</a>'
    >>> u('another', var='fuggetaboutit', content='goto').html
    '<a href="http://localhost/view/another?var=fuggetaboutit">goto</a>'
    >>> u.attr(content='goto').html
    Traceback (most recent call last):
        ....
    ValueError: You must give a content param to <URL http://localhost/view attrs(content="goto")> generate anchor tags
    >>> str(u['foo=bar%20stuff'])
    'http://localhost/view?foo=bar+stuff'
    """

    default_params = {'tag': 'a'}

    def __str__(self):
        return self.href

    def _get_content(self):
        if not self.params.get('content'):
            raise ValueError(
                "You must give a content param to %r generate anchor tags"
                % self)
        return self.params['content']

    def _add_vars(self, vars):
        url = self
        for name in ('confirm', 'content'):
            if name in vars:
                url = url.param(**{name: vars.pop(name)})
        if 'target' in vars:
            url = url.attr(target=vars.pop('target'))
        return url.var(**vars)

    def _add_positional(self, args):
        return self.addpath(*args)

    def _html_attrs(self):
        attrs = self.attrs.items()
        attrs.insert(0, ('href', self.href))
        if self.params.get('confirm'):
            attrs.append(('onclick', 'return confirm(%s)'
                          % js_repr(self.params['confirm'])))
        return attrs

    def onclick_goto__get(self):
        return 'location.href=%s; return false' % js_repr(self.href)

    onclick_goto = property(onclick_goto__get)

    def button__get(self):
        return self.become(Button)

    button = property(button__get)

    def js_popup__get(self):
        return self.become(JSPopup)

    js_popup = property(js_popup__get)
            
class Image(URLResource):

    r"""
    >>> i = Image('/images')
    >>> i = i / '/foo.png'
    >>> i.html
    '<img src="/images/foo.png" />'
    >>> str(i['alt=foo'])
    '<img src="/images/foo.png" alt="foo" />'
    >>> i.href
    '/images/foo.png'
    """
    
    default_params = {'tag': 'img'}

    def __str__(self):
        return self.html

    def _get_content(self):
        return None

    def _add_vars(self, vars):
        return self.attr(**vars)

    def _add_positional(self, args):
        return self.addpath(*args)

    def _html_attrs(self):
        attrs = self.attrs.items()
        attrs.insert(0, ('src', self.href))
        return attrs

class Button(URLResource):

    r"""
    >>> u = URL('/')
    >>> u = u / 'delete'
    >>> b = u.button['confirm=Sure?'](id=5, content='del')
    >>> str(b)
    '<button onclick="if (confirm(\'Sure?\')) {location.href=\'/delete?id=5\'}; return false">del</button>'
    """

    default_params = {'tag': 'button'}

    def __str__(self):
        return self.html

    def _get_content(self):
        if self.params.get('content'):
            return self.params['content']
        if self.attrs.get('value'):
            return self.attrs['content']
        # @@: Error?
        return None

    def _add_vars(self, vars):
        button = self
        if 'confirm' in vars:
            button = button.param(confirm=vars.pop('confirm'))
        if 'content' in vars:
            button = button.param(content=vars.pop('content'))
        return button.var(**vars)

    def _add_positional(self, args):
        return self.addpath(*args)

    def _html_attrs(self):
        attrs = self.attrs.items()
        onclick = 'location.href=%s' % js_repr(self.href)
        if self.params.get('confirm'):
            onclick = 'if (confirm(%s)) {%s}' % (
                js_repr(self.params['confirm']), onclick)
        onclick += '; return false'
        attrs.insert(0, ('onclick', onclick))
        return attrs

class JSPopup(URLResource):

    r"""
    >>> u = URL('/')
    >>> u = u / 'view'
    >>> j = u.js_popup(content='view')
    >>> j.html
    '<a href="/view" onclick="window.open(\'/view\', \'_blank\'); return false" target="_blank">view</a>'
    """

    default_params = {'tag': 'a', 'target': '_blank'}

    def _add_vars(self, vars):
        button = self
        for var in ('width', 'height', 'stripped', 'content'):
            if var in vars:
                button = button.param(**{var: vars.pop(var)})
        return button.var(**vars)

    def _window_args(self):
        p = self.params
        features = []
        if p.get('stripped'):
            p['location'] = p['status'] = p['toolbar'] = '0'
        for param in 'channelmode directories fullscreen location menubar resizable scrollbars status titlebar'.split():
            if param not in p:
                continue
            v = p[param]
            if v not in ('yes', 'no', '1', '0'):
                if v:
                    v = '1'
                else:
                    v = '0'
            features.append('%s=%s' % (param, v))
        for param in 'height left top width':
            if not p.get(param):
                continue
            features.append('%s=%s' % (param, p[param]))
        args = [self.href, p['target']]
        if features:
            args.append(','.join(features))
        return ', '.join(map(js_repr, args))

    def _html_attrs(self):
        attrs = self.attrs.items()
        onclick = ('window.open(%s); return false'
                   % self._window_args())
        attrs.insert(0, ('target', self.params['target']))
        attrs.insert(0, ('onclick', onclick))
        attrs.insert(0, ('href', self.href))
        return attrs

    def _get_content(self):
        if not self.params.get('content'):
            raise ValueError(
                "You must give a content param to %r generate anchor tags"
                % self)
        return self.params['content']

    def _add_positional(self, args):
        return self.addpath(*args)

if __name__ == '__main__':
    import doctest
    doctest.testmod()
    
