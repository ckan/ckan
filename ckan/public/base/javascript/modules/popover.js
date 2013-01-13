this.ckan.module('popover', function (jQuery, _) {
  return {
    initialize: function () {
      var id = this.el.prop('href').replace(/.+\#/, '');
      var content = jQuery('#' + id).html();

      if (content) {
        this.el.popover({
          title: jQuery('#' + id).attr('title'),
          content: content
        });
      }
    }
  };
});
