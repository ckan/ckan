(function (jQuery) {
  // Cache an empty constructor function for it's prototype object.
  function DummyObject() {}

  // Simple cross browser Object.create().
  function create(proto) {
    if (typeof proto !== 'object') {
      return {};
    }
    else if (Object.create) {
      return Object.create(proto);
    }

    DummyObject.prototype = proto;
    return new DummyObject();
  }

  /* A simple helper for sub classing objects. Works in the same way
   * as Backbone.extend() for example.
   *
   * parent     - A constructor function to extend.
   * methods    - An object of prototype methods/properties.
   * properties - An object of static methods/properties.
   *
   *
   * Examples
   *
   *   function MyClass() {}
   *
   *   var ChildClass = jQuery.inherit(MyClass, {
   *     method: function () {}
   *   });
   *
   * Returns a new Constructor function.
   */
  jQuery.inherit = function (parent, methods, properties) {
    methods = methods || {};

    function Object() {
      parent.apply(this, arguments);
    }

    var Child = methods.hasOwnProperty('constructor') ? methods.constructor : Object;

    Child.prototype = create(parent.prototype);
    Child.prototype.constructor = Child;

    jQuery.extend(Child.prototype, methods);

    return jQuery.extend(Child, parent, properties, {__super__: parent.prototype});
  };
})(this.jQuery);
