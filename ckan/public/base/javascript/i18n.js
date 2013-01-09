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

  ckan.i18n = new Jed({
    domain: 'ckan',
    locale_data: {
      ckan: domain
    }
  });

  ckan.i18n.translate = jQuery.proxy(ckan.i18n.translate, ckan.i18n);

  ckan.i18n.load = function (data) {
    if (data && data['']) {
      // Extend our default domain data with the new keys.
      jQuery.extend(domain, data);;
    }
  };

  ckan.sandbox.extend({
    /* An alias for ckan.i18n */
    i18n: ckan.i18n,

    /* An alias for ckan.l18n.translate() */
    translate: ckan.i18n.translate
  });
})(this.ckan, this.jQuery, this.Jed);
