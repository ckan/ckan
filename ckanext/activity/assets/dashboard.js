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

      this.button.popover = new bootstrap.Popover(document.querySelector('#followee-filter .btn'), {
          placement: 'bottom',
          html: true,
          template: '<div class="popover" role="tooltip"><div class="popover-arrow"></div><h3 class="popover-header"></h3><div class="popover-body followee-container"></div></div>',
          customClass: 'popover-followee',
          sanitizeFn: function (content) {
            return DOMPurify.sanitize(content, { ALLOWED_TAGS: [
              "form", "div", "input", "footer", "header", "h1", "h2", "h3", "h4",
              "small", "span", "strong", "i", 'a', 'li', 'ul','p'

            ]});
          },
          content: $('#followee-content').html()
        });
      this.button.prop('title', title);
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
      this.popover = this.button.popover.tip;
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
