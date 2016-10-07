# encoding: utf-8

import ckan
from ckan.plugins import SingletonPlugin, implements, IPackageController
from ckan.plugins import IGroupController, IOrganizationController, ITagController, IResourceController

from ckan.common import request, config, c
from ckan.logic import get_action

LANGS = ['en', 'fr', 'de', 'es', 'it', 'nl', 'ro', 'pt', 'pl']

def translate_data_dict(data_dict):
    '''Return the given dict (e.g. a dataset dict) with as many of its fields
    as possible translated into the desired or the fallback language.

    '''
    desired_lang_code = request.environ['CKAN_LANG']
    fallback_lang_code = config.get('ckan.locale_default', 'en')

    # Get a flattened copy of data_dict to do the translation on.
    flattened = ckan.lib.navl.dictization_functions.flatten_dict(
            data_dict)

    # Get a simple flat list of all the terms to be translated, from the
    # flattened data dict.
    terms = set()
    for (key, value) in flattened.items():
        if value in (None, True, False):
            continue
        elif isinstance(value, basestring):
            terms.add(value)
        elif isinstance(value, (int, long)):
            continue
        else:
            for item in value:
                if isinstance(value, dict):
                    if key == (u'organization',) and item == 'description':
                        terms.add(value[item])
                    else:
                        terms.add(item)
                else:
                    terms.add(item)

    # Get the translations of all the terms (as a list of dictionaries).
    translations = get_action('term_translation_show')(
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
            if value in desired_translations:
                translated_flattened[key] = desired_translations[value]
            else:
                translated_flattened[key] = fallback_translations.get(
                        value, value)

        elif isinstance(value, (int, long, dict)):
            if key == (u'organization',):
                translated_flattened[key] = translate_data_dict(value);
            else:
                translated_flattened[key] = value

        else:
            translated_value = []
            for item in value:
                if item in desired_translations:
                    translated_value.append(desired_translations[item])
                else:
                    translated_value.append(
                        fallback_translations.get(item, item)
                    )
            translated_flattened[key] = translated_value

    # Finally unflatten and return the translated data dict.
    translated_data_dict = (ckan.lib.navl.dictization_functions
            .unflatten(translated_flattened))
    return translated_data_dict

def translate_resource_data_dict(data_dict):
    '''Return the given dict with as many of its fields
    as possible translated into the desired or the fallback language.

    '''
    desired_lang_code = request.environ['CKAN_LANG']
    fallback_lang_code = config.get('ckan.locale_default', 'en')

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
        elif isinstance(value, (int, long)):
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
            if value in desired_translations:
                translated_flattened[key] = desired_translations[value]
            elif value in fallback_translations:
                translated_flattened[key] = fallback_translations.get(value, value)
            else:
                translated_flattened[key] = value

        elif value in (None, True, False):
            # Don't try to translate values that aren't strings.
            translated_flattened[key] = value

        elif isinstance(value, basestring):
            if value in desired_translations:
                translated_flattened[key] = desired_translations[value]
            else:
                translated_flattened[key] = fallback_translations.get(
                        value, value)

        elif isinstance(value, (int, long, dict)):
            translated_flattened[key] = value

        else:
            translated_value = []
            for item in value:
                if item in desired_translations:
                    translated_value.append(desired_translations[item])
                else:
                    translated_value.append(
                        fallback_translations.get(item, item)
                    )
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
             config.get('ckan.locale_default', 'en')
        )

        ## translate title
        title = search_data.get('title')
        search_data['title_' + default_lang] = title
        title_translations = get_action('term_translation_show')(
                          {'model': ckan.model},
                          {'terms': [title],
                              'lang_codes': LANGS})

        for translation in title_translations:
            title_field = 'title_' + translation['lang_code']
            search_data[title_field] = translation['term_translation']

        ## translate rest
        all_terms = []
        for key, value in search_data.iteritems():
            if key in KEYS_TO_IGNORE or key.startswith('title'):
                continue
            if not isinstance(value, list):
                value = [value]
            for item in value:
                if isinstance(item, basestring):
                    all_terms.append(item)

        field_translations = get_action('term_translation_show')(
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

        try:
            current_lang = request.environ['CKAN_LANG']
        except TypeError as err:
            if err.message == ('No object (name: request) has been registered '
                               'for this thread'):
                # This happens when this code gets called as part of a paster
                # command rather then as part of an HTTP request.
                current_lang = config.get('ckan.locale_default')
            else:
                raise

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

        # Translate the unselected search facets.
        facets = search_results.get('search_facets')
        if not facets:
            return search_results

        desired_lang_code = request.environ['CKAN_LANG']
        fallback_lang_code = config.get('ckan.locale_default', 'en')

        # Look up translations for all of the facets in one db query.
        terms = set()
        for facet in facets.values():
            for item in facet['items']:
                terms.add(item['display_name'])
        translations = get_action('term_translation_show')(
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

    def before_view(self, dataset_dict):

        # Translate any selected search facets (e.g. if we are rendering a
        # group read page or the dataset index page): lookup translations of
        # all the terms in c.fields (c.fields contains the selected facets)
        # and save them in c.translated_fields where the templates can
        # retrieve them later.
        desired_lang_code = request.environ['CKAN_LANG']
        fallback_lang_code = config.get('ckan.locale_default', 'en')
        terms = [value for param, value in c.fields]
        translations = get_action('term_translation_show')(
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

        # Now translate the fields of the dataset itself.
        return translate_data_dict(dataset_dict)

class MultilingualGroup(SingletonPlugin):
    '''The MultilingualGroup plugin translates group names and other group
    fields on group read pages and on the group index page.

    For example on the page /de/group/david the title "Dave's Books" at the
    top of the page might be translated to "Dave's Bucher".

    Datasets are also shown on group pages, but these are translated by the
    MultilingualDataset plugin.

    '''
    implements(IGroupController, inherit=True)
    implements(IOrganizationController, inherit=True)

    def before_view(self, data_dict):
        translated_data_dict = translate_data_dict(data_dict)
        return translated_data_dict

class MultilingualTag(SingletonPlugin):
    '''The MultilingualTag plugin translates tag names on tag read pages and
    on the tag index page.

    For example on the page /de/tag/tolstoy the title "Tag: tolstoy" at the
    top of the page might be translated to "Tag: Tolstoi".

    Datasets are also shown on tag pages, but these are translated by the
    MultilingualDataset plugin.

    '''
    implements(ITagController, inherit=True)

    def before_view(self, data_dict):
        translated_data_dict = translate_data_dict(data_dict)
        return translated_data_dict

class MultilingualResource(SingletonPlugin):
   '''The MultilinguaResource plugin translate the selected resource name and description on resource
   preview page.

   '''
   implements(IResourceController, inherit=True)

   def before_show(self, data_dict):
        translated_data_dict = translate_resource_data_dict(data_dict)
        return translated_data_dict
