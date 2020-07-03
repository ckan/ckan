/* User Dashboard
 * Handles the filter dropdown menu and the reduction of the notifications number
 * within the header to zero
 *
 * Examples
 *
 *   <div data-module="dashboard"></div>
 *
 */
this.ckan.module('dashboard', function ($) {
  return {
    button: null,
    popover: null,
    searchTimeout: null,

    /* Initialises the module setting up elements and event listeners.
     *
     * Returns nothing.
     */
    initialize: function () {
      $.proxyAll(this, /_on/);
      this.button = $('#followee-filter .btn').
        on('click', this._onShowFolloweeDropdown);
      var title = this.button.prop('title');

      var myDefaultWhiteList = $.fn.popover.Constructor.DEFAULTS.whiteList
      myDefaultWhiteList.input = []
      myDefaultWhiteList.li = ['data-search']

      this.button.popover({
          placement: 'bottom',
          title: 'Filter',
          html: true,
          content: $('#followee-popover').html()
        });
      this.button.prop('title', title);
      this.popover = this.button.data('bs.popover').tip().addClass('popover-followee');
    },

    /* Handles click event on the 'show me:' dropdown button
     *
     * Returns nothing.
     */
    _onShowFolloweeDropdown: function() {
      this.button.toggleClass('active');
      if (this.button.hasClass('active')) {
        setTimeout(this._onInitSearch, 100);
      }
      return false;
    },

    /* Handles focusing on the input and making sure that the keyup
     * even is applied to the input
     *
     * Returns nothing.
     */
    _onInitSearch: function() {
      var input = $('input', this.popover);
      if (!input.hasClass('inited')) {
        input.
          on('keyup', this._onSearchKeyUp).
          addClass('inited');
      }
      input.focus();
    },

    /* Handles the keyup event
     *
     * Returns nothing.
     */
    _onSearchKeyUp: function() {
      clearTimeout(this.searchTimeout);
      this.searchTimeout = setTimeout(this._onSearchKeyUpTimeout, 300);
    },

    /* Handles the actual filtering of search results
     *
     * Returns nothing.
     */
    _onSearchKeyUpTimeout: function() {
      var input = $('input', this.popover);
      var q = input.val().toLowerCase();
      if (q) {
        $('li', this.popover).hide();
        $('li.everything, [data-search^="' + q + '"]', this.popover).show();
      } else {
        $('li', this.popover).show();
      }
    }
  };
});
