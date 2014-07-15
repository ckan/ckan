// pdf preview module
ckan.module('pdfpreview', function (jQuery) {
  return {
    initialize: function () {
      // set pdfjs worker uri
      PDFJS.workerSrc = pdfjs_workerSrc;

      // use CORS, if supported by browser and server
      if (jQuery.support.cors && preload_resource['original_url'] !== undefined) {
        jQuery.ajax(preload_resource['original_url'], {
          type: 'HEAD',
          success: function(message,text,response){
            loadPdfJsView({
              file: preload_resource['original_url']
            });
          },
          error: function() {
            loadPdfJsView({
              file: preload_resource['url']
            });
          }
        });
      } else {
        loadPdfJsView({
          file: preload_resource['url']
        });
      }
    }
  };
});
