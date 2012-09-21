var CKAN = CKAN || {};

CKAN.View = CKAN.View || {};
CKAN.Model = CKAN.Model || {};
CKAN.Utils = CKAN.Utils || {};
CKAN.Strings = CKAN.Strings || {};

(function ($) {
  $(document).ready(function () {
    CKAN.PdfPreview.loadPreview(preload_resource);
  });
}(jQuery));

/* =================== */
/* == PDF Previewer == */
/* =================== */
CKAN.PdfPreview = function ($, pdf, my) {
  my.dialogId = 'ckanext-pdfpreview';

  // **Public: Opens a pdf preview**
  //
  // Returns nothing.
  my.loadPreview = function(resourceData) {
    var params = {
      file: resourceData['url']
    };

    pdf(params);
  };

  // Export the CKANEXT object onto the window.
  $.extend(true, window, {CKANEXT: {}});
  CKANEXT.PDFPREVIEW = my;
  return my;
}(jQuery, loadPdfJsView, CKAN.PdfPreview || {});
