import re

import ckan.lib.base as base
import ckan.lib.i18n as i18n
import ckan.lib.helpers as h
from ckan.common import _, request


class UtilController(base.BaseController):
    ''' Controller for functionality that has no real home'''

    def redirect(self):
        ''' redirect to the url parameter. '''
        url = base.request.params.get('url')
        if not url:
            base.abort(400, _('Missing Value') + ': url')

        if h.url_is_local(url):
            return base.redirect(url)
        else:
            base.abort(403, _('Redirecting to external site is not allowed.'))

    def primer(self):
        ''' Render all html components out onto a single page.
        This is useful for development/styling of ckan. '''
        return base.render('development/primer.html')

    def set_timezone_offset(self, offset):
        ''' save the users UTC timezone offset in the beaker session '''
        # check if the value can be successfully casted to an int
        try:
            offset = int(offset)
            # UTC offsets are between UTC-12 until UTC+14
            if not (60*12 >= offset >= -(60*14)):
                raise ValueError
        except ValueError:
            base.abort(400, _('Not a valid UTC offset value, must be between 720 (UTC-12) and -840 (UTC+14)'))

        session = request.environ['beaker.session']
        session['utc_offset_mins'] = offset
        session.save()
        return h.json.dumps({'utc_offset_mins': session.get('utc_offset_mins', 'No offset set')})

    def markup(self):
        ''' Render all html elements out onto a single page.
        This is useful for development/styling of ckan. '''
        return base.render('development/markup.html')

    def i18_js_strings(self, lang):
        ''' This is used to produce the translations for javascript. '''
        i18n.set_lang(lang)
        html = base.render('js_strings.html', cache_force=True)
        html = re.sub('<[^\>]*>', '', html)
        header = "text/javascript; charset=utf-8"
        base.response.headers['Content-type'] = header
        return html
