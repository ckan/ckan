// json preview module
ckan.module('jsonpreview', function (jQuery, _) {
  return {
    initialize: function () {
      var self = this;
      $.getJSON(preload_resource['url'], function(data) {
        var html = JSON.stringify(data, null, 4);
        $(self.el).html(html);
      });
    }
  };
});