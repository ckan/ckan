// a simple module that makes bootstrap alerts dismissable via javascript

ckan.module('dismiss-alerts', {
  initialize: function () {
    $(".alert").alert();
  },
    teardown: function () {
  }
});