// data viewer module
// resizes the iframe when the content is loaded
this.ckan.module('data-viewer', function (jQuery) {
  return {
    options: {
      timeout: 200,
      minHeight: 400,
      padding: 42
    },

    initialize: function () {
      jQuery.proxyAll(this, /_on/);
      this.el.on('load', this._onLoad);
      this._FirefoxFix();
    },

    _onLoad: function() {
      var self = this;
      var loc = $('body').data('site-root');
      // see if page is in part of the same domain
      if (this.el.attr('src').substring(0, loc.length) === loc) {
        this._recalibrate();
        setInterval(function() {
          if (!self.el.is(':animated')) {
            self._recalibrate();
          }
        }, this.options.timeout);
      } else {
        this.el.animate({height: 600}, 600);
      }
    },

    _showDebugInfo: function() {
      var iframe = this.el;
      console.log('=================');
      console.log($(iframe.get(0), window.top.document).contents().find('body')[0].scrollHeight);
      console.log($(iframe.get(0).contentWindow.document).height());
      console.log($(iframe.get(0).contentWindow.document.body).height());
      console.log($(iframe.contents().height()));
      console.log($(iframe.contents().innerHeight()));
      console.log($(iframe.contents().find('html').height()));
      console.log($(iframe.contents().find('body').height()));
      console.log($(iframe.contents().find('body').innerHeight()));
    },

    _recalibrate: function() {
      // save reference to this to use in timeout
      var self = this;
      var height = self.el.contents().find('body').height();
      height = Math.max(height, self.options.minHeight);
      var deltaHeight = height - (self.el.height() - self.options.padding);
      if (deltaHeight > 1 || deltaHeight < -10) {
        self.el.animate({height: height+self.options.padding}, Math.min(700, height*2));
      }
    },

    // firefox caches iframes so force it to get fresh content
    _FirefoxFix: function() {
      if(/#$/.test(this.el.src)) {
        this.el.src = this.el.src.substr(0, this.src.length - 1);
      } else {
        this.el.src = this.el.src + '#';
      }
    }
  };
});
