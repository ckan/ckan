/* Table toggle more
 * When a table has more things to it that need to be hidden and then shown more
 */
this.ckan.module('resource-views', function($, _) {
  return {
    /* options object can be extended using data-module-* attributes */
    options: {
      view: false,
      i18n: {
        show_more: _('Show more')
      }
    },

    /* Initialises the module setting up elements and event listeners.
     *
     * Returns nothing.
     */
    initialize: function () {
      $.proxyAll(this, /_/);
      $('nav', this.el).removeClass('hide');
      if (!this.options.view) {
        this.options.view = $('.resource-view:first', this.el).data('id');
      }
      $('.view-list a').on('click', this._handleView);
      this._show();
    },

    _handleView: function (e) {
      e.preventDefault();
      this.options.view = $(e.currentTarget).data('id');
      this._show();
    },

    _show: function () {
      var selector = '[data-id="' + this.options.view + '"]';
      // Hide all the other views
      $('.resource-view', this.el).hide();
      // Now show the relevant one
      $('.resource-view' + selector).show();
      // Now do the same for the nav
      $('.view-list li', this.el).removeClass('active');
      $('.view-list a' + selector, this.el).parent().addClass('active');
    }

  }
});
