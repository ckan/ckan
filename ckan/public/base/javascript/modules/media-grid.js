/* Media Grid
 * Super simple plugin that waits for all the images to be loaded in the media
 * grid and then applies the jQuery.masonry to then
 *
 * This is maintained for compatibility in extensions but it is no longer used
 * in CKAN core.
 */
this.ckan.module('media-grid', function ($) {
  return {
    initialize: function () {
      var wrapper = this.el;
      wrapper.imagesLoaded(function() {
        wrapper.masonry({
          itemSelector: '.media-item'
        });
      });
    }
  };
});
