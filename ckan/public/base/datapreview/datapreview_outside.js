var CKAN = CKAN || {};

(function ($) {
  $(document).ready(function () {
    CKAN.DataPreviewIframe.attachToIframe();
  });
}(jQuery));

/* =========================== */
/* == Data Previewer Iframe == */
/* =========================== */
CKAN.DataPreviewIframe = function ($, my) {
  my.$iframes = $('.ckanext-datapreview-iframe');

  // **Public: Attaches lad listener to preview iframes**
  //
  // Returns nothing.
  my.attachToIframe = function() {
    $.each(my.$iframes, function(index, iframe) {
      iframe = $(iframe);
      iframe.load(function() {
        loc = window.location.protocol+'//'+window.location.host;
        if (iframe.attr('src').substring(0, loc.length) === loc) {
          recalibrate();
          iframe.contents().find('body').resize(function() {
            recalibrate();
          });
        }
        else {
          console.log('set size manually');
          iframe.animate({height: 600}, 600);
        }
      });

      var resizeTimer;
      var recalibrate = function() {
        resizeTimer = setTimeout(function() {
          resize(iframe);
        }, 100);
      };
    });
  };

  // ** Public: resizes a data preview iframe to match the content
  var resize = function(iframe) {
    var self = iframe;
    offset = 0;
    var height = iframe.contents().height();
    iframe.animate({height: height+offset}, height);
  };

  // ** Public: connect to child iframe context
  my.getChild = function(iframe) {
    return $(iframe)[0].contentWindow;
  };

  // Export the CKANEXT object onto the window.
  $.extend(true, window, {CKANEXT: {}});
  CKANEXT.DATAPREVIEW = my;
  return my;
}(jQuery, CKAN.DataPreview || {});