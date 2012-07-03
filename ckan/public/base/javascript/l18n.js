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
