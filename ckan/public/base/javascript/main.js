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

  /* Returns a full url for the current site with the provided path appended.
   *
   * path          - A path to append to the url (default: '/')
   * includeLocale - If true the current locale will be added to the page.
   *
   * Examples
   *
   *   var imageUrl = sandbox.url('/my-image.png');
   *   // => http://example.ckan.org/my-image.png
   *
   *   var imageUrl = sandbox.url('/my-image.png', true);
   *   // => http://example.ckan.org/en/my-image.png
   *
   *   var localeUrl = sandbox.url(true);
   *   // => http://example.ckan.org/en
   *
   * Returns a url string.
   */
  ckan.url = function (path, includeLocale) {
    if (typeof path === 'boolean') {
      includeLocale = path;
      path = '';
    }

    path = path.replace(/^\//, '');

    var root = includeLocale ? ckan.SITE_ROOT : ckan.LOCALE_ROOT;
    return path ? root + '/' + path : root;
  };

  ckan.sandbox.extend({url: ckan.url});

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
