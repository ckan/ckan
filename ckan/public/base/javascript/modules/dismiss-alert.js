// a simple module that makes bootstrap alerts dismissable via javascript

ckan.module('dismiss-alert', function (jQuery){
  initialize: function () {
    this.el.alert();
  },
    teardown: function () {
  }
});