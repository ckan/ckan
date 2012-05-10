import re
import ckan.lib.base as base
import ckan.lib.i18n as i18n

class I18NController(base.BaseController):

    def strings(self, lang):
        i18n.set_lang(lang)
        html = base.render('js_strings.html', cache_force=True)
        html = re.sub('<[^\>]*>', '', html)
        base.response.headers['Content-type'] = "text/javascript; charset=utf-8"
        return html
