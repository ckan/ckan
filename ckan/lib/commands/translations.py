import os
import re

from ckan.lib.commands import CkanCommand


class TranslationsCommand(CkanCommand):
    '''Translation helper functions

    trans js      - generate the javascript translations
    trans mangle  - mangle the zh_TW translations for testing
    '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 1
    min_args = 1

    def command(self):
        self._load_config()
        from pylons import config
        self.ckan_path = os.path.join(os.path.dirname(__file__), '..')
        i18n_path = os.path.join(self.ckan_path, 'i18n')
        self.i18n_path = config.get('ckan.i18n_directory', i18n_path)
        command = self.args[0]
        if command == 'mangle':
            self.mangle_po()
        elif command == 'js':
            self.build_js_translations()
        else:
            print 'command not recognised'

    def po2dict(self, po, lang):
        '''Convert po object to dictionary data structure (ready for JSON).

        This function is from pojson
        https://bitbucket.org/obviel/pojson

Copyright (c) 2010, Fanstatic Developers
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of the <organization> nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL FANSTATIC DEVELOPERS BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''
        result = {}

        result[''] = {}
        result['']['plural-forms'] = po.metadata['Plural-Forms']
        result['']['lang'] = lang
        result['']['domain'] = 'ckan'

        for entry in po:
            if entry.obsolete:
                continue
            # check if used in js file we only include these
            occurrences = entry.occurrences
            js_use = False
            for occurrence in occurrences:
                if occurrence[0].endswith('.js'):
                    js_use = True
                    continue
            if not js_use:
                continue
            if entry.msgstr:
                result[entry.msgid] = [None, entry.msgstr]
            elif entry.msgstr_plural:
                plural = [entry.msgid_plural]
                result[entry.msgid] = plural
                ordered_plural = sorted(entry.msgstr_plural.items())
                for order, msgstr in ordered_plural:
                    plural.append(msgstr)
        return result

    def build_js_translations(self):
        import polib
        import simplejson as json

        def create_js(source, lang):
            print 'Generating', lang
            po = polib.pofile(source)
            data = self.po2dict(po, lang)
            data = json.dumps(data, sort_keys=True,
                              ensure_ascii=False, indent=2 * ' ')
            out_dir = os.path.abspath(os.path.join(self.ckan_path, 'public',
                                                   'base', 'i18n'))
            out_file = open(os.path.join(out_dir, '%s.js' % lang), 'w')
            out_file.write(data.encode('utf-8'))
            out_file.close()

        for l in os.listdir(self.i18n_path):
            if os.path.isdir(os.path.join(self.i18n_path, l)):
                f = os.path.join(self.i18n_path, l, 'LC_MESSAGES', 'ckan.po')
                create_js(f, l)
        print 'Completed generating JavaScript translations'

    def mangle_po(self):
        ''' This will mangle the zh_TW translations for translation coverage
        testing.

        NOTE: This will destroy the current translations fot zh_TW
        '''
        import polib
        pot_path = os.path.join(self.i18n_path, 'ckan.pot')
        po = polib.pofile(pot_path)
        # we don't want to mangle the following items in strings
        # %(...)s  %s %0.3f %1$s %2$0.3f [1:...] {...} etc

        # sprintf bit after %
        spf_reg_ex = "\+?(0|'.)?-?\d*(.\d*)?[\%bcdeufosxX]"

        extract_reg_ex = '(\%\([^\)]*\)' + spf_reg_ex + \
                         '|\[\d*\:[^\]]*\]' + \
                         '|\{[^\}]*\}' + \
                         '|<[^>}]*>' + \
                         '|\%((\d)*\$)?' + spf_reg_ex + ')'

        for entry in po:
            msg = entry.msgid.encode('utf-8')
            matches = re.finditer(extract_reg_ex, msg)
            length = len(msg)
            position = 0
            translation = u''
            for match in matches:
                translation += '-' * (match.start() - position)
                position = match.end()
                translation += match.group(0)
            translation += '-' * (length - position)
            entry.msgstr = translation
        out_dir = os.path.join(self.i18n_path, 'zh_TW', 'LC_MESSAGES')
        try:
            os.makedirs(out_dir)
        except OSError:
            pass
        po.metadata['Plural-Forms'] = "nplurals=1; plural=0\n"
        out_po = os.path.join(out_dir, 'ckan.po')
        out_mo = os.path.join(out_dir, 'ckan.mo')
        po.save(out_po)
        po.save_as_mofile(out_mo)
        print 'zh_TW has been mangled'
