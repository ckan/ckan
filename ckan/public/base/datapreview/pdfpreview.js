var CKAN = CKAN || {};

CKAN.View = CKAN.View || {};
CKAN.Model = CKAN.Model || {};
CKAN.Utils = CKAN.Utils || {};
CKAN.Strings = CKAN.Strings || {};

(function ($) {
  $(document).ready(function () {
    //CKAN.PdfPreview.loadPreview(preload_resource);
  });
}(jQuery));

/* =================== */
/* == PDF Previewer == */
/* =================== */
CKAN.PdfPreview = function ($, my) {
  my.dialogId = 'ckanext-pdfpreview';

  // **Public: Opens a pdf preview**
  //
  // Returns nothing.
  my.loadPreview = function(resourceData) {
    'use strict';

    // disable worker for now
    // TODO: enable
    PDFJS.disableWorker = true;

    //
    // Fetch the PDF document from the URL using promices
    //
    PDFJS.getDocument(resourceData['url']).then(function(pdf) {
      // Using promise to fetch the page
      pdf.getPage(1).then(function(page) {
        var scale = 1.5;
        var viewport = page.getViewport(scale);

        //
        // Prepare canvas using PDF page dimensions
        //
        var canvas = document.getElementById(my.dialogId);
        var context = canvas.getContext('2d');
        canvas.height = viewport.height;
        canvas.width = viewport.width;

        //
        // Render PDF page into canvas context
        //
        var renderContext = {
          canvasContext: context,
          viewport: viewport
        };
        page.render(renderContext);
      });
    });
  }

  // Export the CKANEXT object onto the window.
  $.extend(true, window, {CKANEXT: {}});
  CKANEXT.PDFPREVIEW = my;
  return my;
}(jQuery, CKAN.PdfPreview || {});
