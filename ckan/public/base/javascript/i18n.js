this.ckan = this.ckan || {};

// Fake localisation function. A basic drop in for Jed.
// See: http://slexaxton.github.com/Jed/
this.ckan.i18n = {
  translate: function (string) {
    return {
      fetch: function () {
        return string;
      }
    };
  }
};

this.ckan.sandbox.extend({
  /* An alias for ckan.i18n */
  i18n: this.ckan.i18n,

  /* An alias for ckan.l18n.translate() */
  translate: this.ckan.i18n.translate
});
