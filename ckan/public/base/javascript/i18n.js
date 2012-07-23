this.ckan = this.ckan || {};

(function (ckan, jQuery, Jed) {
  // Fake localisation function. A basic drop in for Jed.
  // See: http://slexaxton.github.com/Jed/
  ckan.i18n = new Jed({});
  ckan.i18n.translate = jQuery.proxy(ckan.i18n.translate, ckan.i18n);

  ckan.sandbox.extend({
    /* An alias for ckan.i18n */
    i18n: ckan.i18n,

    /* An alias for ckan.l18n.translate() */
    translate: ckan.i18n.translate
  });
})(this.ckan, this.jQuery, this.Jed);
