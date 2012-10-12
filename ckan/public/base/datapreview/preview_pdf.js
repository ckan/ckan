// pdf preview module
ckan.module('pdfpreview', function () {
  return {
    initialize: function () {
      // set pdfjs worker uri
      PDFJS.workerSrc = pdfjs_workerSrc;

      var params = {
        file: preload_resource['url']
      };

      loadPdfJsView(params);
    }
  };
});
