// data viewer module
// resizes the iframe when the content is loaded
this.ckan.module('data-viewer', function (jQuery, _) {
  return {
    initialize: function () {
      jQuery.proxyAll(this, /_on/);
      this.el.on('load', this._onLoad);
      this._FirefoxFix();
    },

    _onLoad: function() {
      var that = this;
      var loc = $('body').data('site-root');
      // see if page is in part of the same domain
      if (this.el.attr('src').substring(0, loc.length) === loc) {
        this._recalibrate();
        this.el.contents().find('body').resize(function() {
          // this might break in firefox on the graph page
          that._recalibrate();
        });
      }
      else {
        this.el.animate({height: 600}, 600);
      }
    },

    _recalibrate: function() {
      // save reference to this to use in timeout
      var that = this;
      resizeTimer = setTimeout(function() {
        var height = that.el.contents().find('body').height();
        that.el.animate({height: height+2}, Math.min(700, height*2));
      }, 100);
    },

    // firefox caches iframes so force it to get fresh content
    _FirefoxFix: function() {
      if(/#$/.test(this.el.src)){
        this.el.src = this.el.src.substr(0, this.src.length - 1);
      } else {
        this.el.src = this.el.src + '#';
      }
    }
  };
});
