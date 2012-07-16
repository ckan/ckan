this.ckan.module('resource-form', function (jQuery, _) {
  return {
    initialize: function () {
      jQuery.proxyAll(this, /_on/);
      this.sandbox.subscribe('resource:uploaded', this._onResourceUploaded);
    },
    teardown: function () {
      this.sandbox.unsubscribe('resource:uploaded', this._onResourceUploaded);
    },
    _onResourceUploaded: function (resource) {
      for (var key in resource) {
        if (resource.hasOwnProperty(key)) {
          this.$('[name="' + key + '"]').val(resource[key]);
        }
      }
    }
  };
});
