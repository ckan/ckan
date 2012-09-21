var CKAN = CKAN || {};

(function ($) {
  $(document).ready(function () {
    CKAN.JsonPreview.loadPreview(preload_resource);
  });
}(jQuery));

/* ==================== */
/* == JSON Previewer == */
/* ==================== */
CKAN.JsonPreview = function ($, my) {
  my.dialogId = 'ckanext-jsonpreview';

  // **Public: Loads the json preview **
  //
  // Returns nothing.
  my.loadPreview = function(resourceData) {

    $.getJSON(resourceData['url'], function(data) {
      var html = JSON.stringify(data, null, 4);
      $('#'+my.dialogId).html(html);
    });
  };

  // Export the CKANEXT object onto the window.
  $.extend(true, window, {CKANEXT: {}});
  CKANEXT.JSONPREVIEW = my;
  return my;
}(jQuery, CKAN.JsonPreview || {});
