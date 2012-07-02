// Global ckan namespace
this.ckan = this.ckan || {};

// Fake localisation function.
this.ckan.trans = function (string) {
  return string;
};

this.ckan.module = function (name, factory, defaults) {
  factory.defaults = defaults || {};
  this.modules[name] = factory;
};

this.ckan.modules = {};
this.ckan.setup = function () {
  var modules = this.modules;
  var _this = this;

  jQuery('[data-module]').each(function () {
    var data = $(this).data();
    var module = modules[data.module];
    var options = jQuery.extend({}, module.defaults || {});
    var prefix = 'module';
    var key;
    var sandbox;
    var prop;

    if (module && typeof module === 'function') {
      for (key in data) {
        if (key !== prefix && key.indexOf(prefix) === 0) {
          prop = key.slice(prefix.length);
          prop = prop[0].toLowerCase() + prop.slice(1);

          options[prop] = data[key];
        }
      }

      sandbox = _this.sandbox(this, options);
      module.call(sandbox, sandbox, sandbox.options, sandbox.trans);
    }
  });
};

jQuery(function () {
  ckan.setup();
});

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
