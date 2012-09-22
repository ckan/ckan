// pdf preview module
ckan.module('pdfpreview', function () {
  return {
    initialize: function () {
      var params = {
        file: preload_resource['url']
      };

      loadPdfJsView(params);
    }
  };
});
