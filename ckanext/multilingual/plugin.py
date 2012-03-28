import sets
import ckan
from ckan.plugins import SingletonPlugin, implements, IPackageController
from ckan.plugins import IGroupController, ITagController
import pylons
import ckan.logic.action.get as action_get
from pylons import config

LANGS = ['en', 'fr', 'de', 'es', 'it', 'nl', 'ro', 'pt', 'pl']

def translate_data_dict(data_dict):
    desired_lang_code = pylons.request.environ['CKAN_LANG']
    fallback_lang_code = pylons.config.get('ckan.locale_default', 'en')

    # Get a flattened copy of data_dict to do the translation on.
    flattened = ckan.lib.navl.dictization_functions.flatten_dict(
            data_dict)

    # Get a simple flat list of all the terms to be translated, from the
    # flattened data dict.
    terms = sets.Set()
    for (key, value) in flattened.items():
        if value in (None, True, False):
            continue
        elif isinstance(value, basestring):
            terms.add(value)
        elif isinstance(value, int):
            continue
        else:
            for item in value:
                terms.add(item)

    # Get the translations of all the terms (as a list of dictionaries).
    translations = ckan.logic.action.get.term_translation_show(
            {'model': ckan.model},
            {'terms': terms,
                'lang_codes': (desired_lang_code, fallback_lang_code)})

    # Transform the translations into a more convenient structure.
    desired_translations = {}
    fallback_translations = {}
    for translation in translations:
        if translation['lang_code'] == desired_lang_code:
            desired_translations[translation['term']] = (
                    translation['term_translation'])
        else:
            assert translation['lang_code'] == fallback_lang_code
            fallback_translations[translation['term']] = (
                    translation['term_translation'])

    # Make a copy of the flattened data dict with all the terms replaced by
    # their translations, where available.
    translated_flattened = {}
    for (key, value) in flattened.items():

        # Don't translate names that are used for form URLs.
        if key == ('name',):
            translated_flattened[key] = value
        elif (key[0] in ('tags', 'groups') and len(key) == 3
                and key[2] == 'name'):
            translated_flattened[key] = value

        elif value in (None, True, False):
            # Don't try to translate values that aren't strings.
            translated_flattened[key] = value

        elif isinstance(value, basestring):
            if desired_translations.has_key(value):
                translated_flattened[key] = desired_translations[value]
            else:
                translated_flattened[key] = fallback_translations.get(
                        value, value)

        elif isinstance(value, int):
            translated_flattened[key] = value

        else:
            translated_value = []
            for item in value:
                if desired_translations.has_key(value):
                    translated_flattened[key] = desired_translations[value]
                else:
                    translated_flattened[key] = fallback_translations.get(
                            value, value)
            translated_flattened[key] = translated_value

    # Finally unflatten and return the translated data dict.
    translated_data_dict = (ckan.lib.navl.dictization_functions
            .unflatten(translated_flattened))
    return translated_data_dict

KEYS_TO_IGNORE = ['state', 'revision_id', 'id', #title done seperately
                  'metadata_created', 'metadata_modified', 'site_id']

class MultilingualDataset(SingletonPlugin):
    implements(IPackageController, inherit=True)

    def before_index(self, search_data):

        default_lang = search_data.get(
            'lang_code', 
             pylons.config.get('ckan.locale_default', 'en')
        )

        ## transloate title
        title = search_data.get('title')
        search_data['title_' + default_lang] = title 
        title_translations = action_get.term_translation_show(
                          {'model': ckan.model},
                          {'terms': [title],
                              'lang_codes': LANGS})

        for translation in title_translations:
            title_field = 'title_' + translation['lang_code']
            search_data[title_field] = translation['term_translation']

        ## transloate rest
        all_terms = []
        for key, value in search_data.iteritems():
            if key in KEYS_TO_IGNORE or key.startswith('title'):
                continue
            if isinstance(value, list):
                all_terms.extend(value)
            elif value in (None, True, False):
                continue
            else:
                all_terms.append(value)

        field_translations = action_get.term_translation_show(
                          {'model': ckan.model},
                          {'terms': all_terms,
                              'lang_codes': LANGS})

        text_field_items = dict(('text_' + lang, []) for lang in LANGS)
        
        text_field_items['text_' + default_lang].extend(all_terms)

        for translation in sorted(field_translations):
            lang_field = 'text_' + translation['lang_code']
            text_field_items[lang_field].append(translation['term_translation'])

        for key, value in text_field_items.iteritems():
            search_data[key] = ' '.join(value)
        
        return search_data

    def before_search(self, search_params):
        lang_set = set(LANGS)
        current_lang = pylons.request.environ['CKAN_LANG']
        # fallback to default locale if locale not in suported langs
        if not current_lang in lang_set:
            current_lang = config.get('ckan.locale_default')
        # fallback to english if default locale is not supported
        if not current_lang in lang_set:
            current_lang = 'en'
        # treat current lang differenly so remove from set
        lang_set.remove(current_lang)

        # weight current lang more highly
        query_fields = 'title_%s^8 text_%s^4' % (current_lang, current_lang)

        for lang in lang_set:
            query_fields += ' title_%s^2 text_%s' % (lang, lang)

        search_params['qf'] = query_fields

        return search_params

    def after_search(self, search_results, search_params):

        facets = search_results.get('new_facets')
        if not facets:
            return search_results

        desired_lang_code = pylons.request.environ['CKAN_LANG']
        fallback_lang_code = pylons.config.get('ckan.locale_default', 'en')

        # Look up all the term translations in one db query.
        terms = sets.Set()
        for facet in facets.values():
            for item in facet['items']:
                terms.add(item['display_name'])
        translations = ckan.logic.action.get.term_translation_show(
                {'model': ckan.model},
                {'terms': terms,
                    'lang_codes': (desired_lang_code, fallback_lang_code)})

        # Replace facet display names with translated ones.
        for facet in facets.values():
            for item in facet['items']:
                matching_translations = [translation for
                        translation in translations
                        if translation['term'] == item['display_name']
                        and translation['lang_code'] == desired_lang_code]
                if not matching_translations:
                    matching_translations = [translation for
                            translation in translations
                            if translation['term'] == item['display_name']
                            and translation['lang_code'] == fallback_lang_code]
                if matching_translations:
                    assert len(matching_translations) == 1
                    item['display_name'] = (
                        matching_translations[0]['term_translation'])

        return search_results

    def before_view(self, data_dict):

        # Lookup translations of all the terms in c.fields, save them in
        # c.translated_fields.
        c = pylons.c
        desired_lang_code = pylons.request.environ['CKAN_LANG']
        fallback_lang_code = pylons.config.get('ckan.locale_default', 'en')
        terms = [value for param, value in c.fields]
        translations = ckan.logic.action.get.term_translation_show(
                {'model': ckan.model},
                {'terms': terms,
                 'lang_codes': (desired_lang_code, fallback_lang_code)})
        c.translated_fields = {}
        for param, value in c.fields:
            matching_translations = [translation for translation in
                    translations if translation['term'] == value and
                    translation['lang_code'] == desired_lang_code]
            if not matching_translations:
                matching_translations = [translation for translation in
                        translations if translation['term'] == value and
                        translation['lang_code'] == fallback_lang_code]
            if matching_translations:
                assert len(matching_translations) == 1
                translation = matching_translations[0]['term_translation']
                c.translated_fields[(param, value)] = translation

        # Translate all the terms in data_dict.
        return translate_data_dict(data_dict)

class MultilingualGroup(SingletonPlugin):
    implements(IGroupController, inherit=True)

    def before_view(self, data_dict):
        return translate_data_dict(data_dict)

class MultilingualTag(SingletonPlugin):
    implements(ITagController, inherit=True)

    def before_view(self, data_dict):
        translated_data_dict = translate_data_dict(data_dict)
        return translated_data_dict
