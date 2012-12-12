this.ckan.module('dashboard', function ($, _) {

  return {
    initialize: function () {
      $.proxyAll(this, /_on/);

      var popover = $('#followee-filter .btn')
        .on('click', function() {
          var $this = $(this);
          $this.toggleClass('active');
          if ($this.hasClass('active')) {
            setTimeout(function() {
              $('input', $this.data('popover').tip()).focus();
            }, 100);
          }
          return false;
        }).
        popover({
          placement: 'bottom',
          title: 'Filter',
          html: true,
          content: $('#followee-popover').html()
        }).
        data('popover').tip().addClass('popover-followee');

      if ($('.new', this.el)) {
        setTimeout(function() {
          $('.masthead .notifications').removeClass('notifications-important').html('0');
        }, 1000);
      }
    }
  };
});
