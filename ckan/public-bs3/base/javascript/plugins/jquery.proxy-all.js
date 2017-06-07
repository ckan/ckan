(function (jQuery) {
  /* Works in a similar fashion to underscore's _.bindAll() but also accepts
   * regular expressions for method names.
   *
   * obj     - An object to proxy methods.
   * args... - Successive method names or regular expressions to bind.
   *
   * Examples
   *
   *   var obj = {
   *     _onClick: function () {}
   *     _onSave: function () {}
   *   };
   *
   *   // Provide method names to proxy/bind to obj scope.
   *   jQuery.bindAll(obj, '_onClick', '_onSave');
   *
   *   // Use a RegExp to match patterns.
   *   jQuery.bindAll(obj, /^_on/);
   *
   * Returns the original object.
   */
  jQuery.proxyAll = function (obj /*, args... */) {
    var methods = [].slice.call(arguments, 1);
    var index = 0;
    var length = methods.length;
    var property;
    var method;

    for (; index < length; index += 1) {
      method = methods[index];

      for (property in obj) {
        if (typeof obj[property] === 'function') {
          if ((method instanceof RegExp && method.test(property)) || property === method) {
            if (obj[property].proxied !== true) {
              obj[property] = jQuery.proxy(obj[property], obj);
              obj[property].proxied = true;
            }
          }
        }
      }
    }

    return obj;
  };
})(this.jQuery);
