this.ckan.module('active-nav-item-scroll', function ($) {
    return {
      initialize: function () {
        console.log("hello")
        var activeTab = this.el.find('li.active');

        if (window.innerWidth <= 768) {
            this.el.animate({
                scrollLeft: activeTab.position().left - this.el.width() / 2 + activeTab.outerWidth() / 2
            }, 500);
        }
      },
    };
  });
  