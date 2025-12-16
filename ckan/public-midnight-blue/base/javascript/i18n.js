'use strict';

/*
 * CKAN JavaScript i18n functionality.
 *
 * Adds an `i18n` attribute to the CKAN object (`this.ckan`).
 *
 * Singular strings can be translated using `i18n._`:
 *
 *     ckan.i18n._('Hello, world!')
 *
 * The function will return the translated string in the currently selected
 * language. Often, a translateable string contains dynamic parts, for example
 * a username. These can be included via named `%`-placeholders:
 *
 *     ckan.i18n._('Hello, %(name)s!', {name: 'Jessica'})
 *
 * After translation the placeholders are replaced using the values passed in
 * the second argument.
 *
 * Plural strings can be translated using `i18n.ngettext`:
 *
 *     ckan.i18n.ngettext('%(num)d item was deleted',
 *                        '%(num)d items were deleted',
 *                        num_items)
 *
 * Here, the first two arguments contain the singular and plural translation
 * strings. The third argument contains the number which is used to decide
 * whether the singular form or the plural form is to be used. The `num`
 * placeholder is special in plural forms and will be replaced with the value
 * of the third argument.
 *
 * As before your strings can contain additional placeholders, and you pass
 * their values using another argument:
 *
 *     ckan.i18n.ngettext('%(name)s deleted %(num)d item',
 *                        '%(name)s deleted %(num)d items',
 *                        num_items,
 *                        {name: 'Thomas'})
 *
 * Note that inside a CKAN JS module you can also use the shortcuts `this._`
 * and `this.ngettext`.
 */

this.ckan = this.ckan || {};

(function (ckan, jQuery, Jed) {
  // See: http://slexaxton.github.com/Jed/
  var domain = {
    "": {
      "domain": "ckan",
      "lang": "en",
      "plural_forms": "nplurals=2; plural=(n != 1);"
    }
  };

  var jed = new Jed({
    domain: 'ckan',
    locale_data: {
      ckan: domain
    }
  });

  ckan.i18n = {};

  /*
   * Expose JED translation interface [DEPRECATED].
   *
   * Using the JED functions directly is deprecated and only kept for
   * backwards-compatibility. Use `_` and `ngettext` instead.
   */
  ckan.i18n.translate = jQuery.proxy(jed.translate, jed);

  /*
   * Internal function to load a translation.
   */
  ckan.i18n.load = function (data) {
    if (data && data['']) {
      // Extend our default domain data with the new keys.
      jQuery.extend(domain, data);;
    }
  };

  ckan.i18n._ = function (string, values) {
    return jed.sprintf(jed.gettext(string), values || {});
  };

  ckan.i18n.ngettext = function(singular, plural, num, values) {
    values = values || {};
    values['num'] = num;
    return jed.sprintf(jed.ngettext(singular, plural, num), values);
  };

  ckan.sandbox.extend({
    /* An alias for ckan.i18n [DEPRECATED] */
    i18n: ckan.i18n,

    /* An alias for ckan.l18n.translate() [DEPRECATED] */
    translate: ckan.i18n.translate
  });
})(this.ckan, this.jQuery, this.Jed);
