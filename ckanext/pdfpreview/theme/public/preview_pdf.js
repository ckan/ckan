// pdf preview module
ckan.module('pdfpreview', function (jQuery) {
  return {
    initialize: function () {
      // set pdfjs worker uri
      PDFJS.workerSrc = pdfjs_workerSrc;

      var resource_url = preload_resource['url'];

      // use CORS, if supported by browser and server
      if (jQuery.support.cors && preload_resource['original_url'] !== undefined) {
        jQuery.ajax({
          type: 'HEAD',
          async: true,
          url: preload_resource['original_url'],
          success: function(message,text,response){
            resource_url = preload_resource['original_url'];
          }
        });
      }

      var params = {
        file: resource_url
      };

      loadPdfJsView(params);
    }
  };
});
