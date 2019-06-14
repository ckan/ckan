# encoding: utf-8

import re

import ckan.lib.base as base
import ckan.lib.i18n as i18n
import ckan.lib.helpers as h
from ckan.common import _


class UtilController(base.BaseController):
    ''' Controller for functionality that has no real home'''

    def redirect(self):
        ''' redirect to the url parameter. '''
        url = base.request.params.get('url')
        if not url:
            base.abort(400, _('Missing Value') + ': url')

        if h.url_is_local(url):
            return h.redirect_to(url)
        else:
            base.abort(403, _('Redirecting to external site is not allowed.'))

    def i18_js_strings(self, lang):
        ''' This is used to produce the translations for javascript. '''
        i18n.set_lang(lang)
        html = base.render('js_strings.html', cache_force=True)
        html = re.sub(r'<[^\>]*>', '', html)
        header = "text/javascript; charset=utf-8"
        base.response.headers['Content-type'] = header
        return html
