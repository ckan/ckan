"use strict";

/* Datapusher popover
 * Handle the popup display in 'resource view page' activity stream
 *
 * Options
 * - title: title of the popover
 * - content: content for the popover
 */
ckan.module('datapusher_popover', function($) {
  return {
    initialize: function() {
      $.proxyAll(this, /_on/);
      this.popover = this.el;
      this.popover.popover({
        html: true,
        title: this.options.title,
        content: this.options.content
      });      
      $(document).on('click', '.popover-close', this._onClose);
    },

    _onClose: function() {
      this.popover.popover('hide');
    }
  };
});