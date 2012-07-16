// Global ckan namespace
this.ckan = this.ckan || {};

(function (ckan, jQuery) {
  ckan.initialize = function () {
    var body = jQuery('body');
    var trailingSlash = /\/$/;
    var location = window.location;
    var root = location.protocol + location.host;

    this.SITE_ROOT   = (body.data('siteRoot') || root).replace(trailingSlash, '');
    this.LOCALE_ROOT = (body.data('localeRoot') || root).replace(trailingSlash, '');

    this.module.initialize();
  };

  jQuery(function () {
    ckan.initialize();
  });
})(this.ckan, this.jQuery);

// Temporary banner to let users on IE7 know that it may not display as
// expected.
(function showIEBanner() {
  function prepend(parent, child) {
    var element = parent.firstChild;

    while (element && element.nodeType > 1) {
      element = element.nextSibling;
    }

    parent.insertBefore(child, element);
  }

  if (document.documentElement.className.indexOf('ie7') > -1) {
    var banner = document.createElement('div');
    var content = document.getElementById('content');

    banner.className = 'alert';
    banner.innerHTML =  '<strong>Notice:</strong> ';
    banner.innerHTML += 'This site is currently in development. ';
    banner.innerHTML += 'Internet Explorer 7 may not display as expected';

    if (content) {
      prepend(content, banner);
    }
  }
})();
