/* Table toggle more
 * When a table has more things to it that need to be hidden and then shown more
 */
this.ckan.module('resource-views', function($, _) {
  return {

    /* Initialises the module setting up elements and event listeners.
     *
     * Returns nothing.
     */
    initialize: function () {
      $.proxyAll(this, /_/);

      this.view = false;
      $('nav', this.el).removeClass('hide');
      $(window).on('hashchange', this._handleHash);

      if (window.location.hash.indexOf('#view-') === 0) {
        this._handleHash();
        var position = $('.view-list li.active', this.el).position();
        if (position.left > 800) {
          $('.view-list', this.el).scrollLeft(position.left);
        }
      } else {
        this.view = $('.resource-view:first', this.el).data('id');
        this._show();
      }
    },

    _handleHash: function () {
      var hash = window.location.hash;
      if (hash.indexOf('#view-') === 0) {
        this.view = hash.substring(6);
        this._show();
      }
    },

    _show: function () {
      // Hide all the other views
      $('.resource-view', this.el).hide();
      // Now show the relevant one
      $('#view-' + this.view).show();
      // Now do the same for the nav
      $('.view-list li', this.el).removeClass('active');
      $('.view-list a[data-id="' + this.view + '"]', this.el).parent().addClass('active');
    }

  }
});
