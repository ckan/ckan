this.ckan.module('dashboard', function ($, _) {
  return {
    button: null,
    popover: null,
    searchTimeout: null,
    initialize: function () {
      $.proxyAll(this, /_on/);
      this.button = $('#followee-filter .btn').
        on('click', this._onShowFolloweeDropdown).
        popover({
          placement: 'bottom',
          title: 'Filter',
          html: true,
          content: $('#followee-popover').html()
        });
      this.popover = this.button.data('popover').tip().addClass('popover-followee');
      if ($('.new', this.el)) {
        setTimeout(function() {
          $('.masthead .notifications').removeClass('notifications-important').html('0');
        }, 1000);
      }
    },
    _onInitSearch: function() {
      var input = $('input', this.popover);
      if (!input.hasClass('inited')) {
        input.
          on('keyup', this._onSearchKeyUp).
          addClass('inited');
      }
      input.focus();
    },
    _onSearchKeyUp: function() {
      clearTimeout(this.searchTimeout);
      this.searchTimeout = setTimeout(this._onSearchKeyUpTimeout, 300);
    },
    _onSearchKeyUpTimeout: function(e) {
      var input = $('input', this.popover);
      var q = input.val().toLowerCase();
      if (q) {
        $('li', this.popover).hide();
        $('li.everything, [data-search^="' + q + '"]', this.popover).show();
      } else {
        $('li', this.popover).show();
      }
    },
    _onShowFolloweeDropdown: function() {
      this.button.toggleClass('active');
      if (this.button.hasClass('active')) {
        setTimeout(this._onInitSearch, 100);
      }
      return false;
    }
  };
});
