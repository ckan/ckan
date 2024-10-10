this.ckan = this.ckan || {};

/* The sandbox is a simple way to give modules access to common functionality
 * while restricting their access to the rest of the document. This is done
 * in an attempt to encourage modular code that has fewer dependencies.
 *
 * The sandbox provides access to the module element and it's children via the
 * .el and .$() properties. Talking to other modules should occur via the
 * .publish() and .subscribe() methods which are shared globally among all
 * instances.
 *
 * Ajax is available via the .ajax() method which is simply the jQuery.ajax()
 * method.
 *
 * Other core libraries can extend all sandbox instances by using the
 * ckan.sandbox.extend() method which extends the Sandbox.prototype. These
 * extensions will then be available to all modules.
 *
 * Examples
 *
 *   var sandbox = ckan.sandbox(jQuery('#module'), {opt1: 1, opt2: 2});
 *
 *   sandbox.$('a'); // Query the module for anchors.
 *   sandbox.subscribe('my-event', callback); // Subscribe to events.
 *   sandbox.publish('other-event'); // Publish to all other instances.
 *
 *   // Extension
 *   ckan.sandbox.extend({
 *     translate: ckan.i18n.translate
 *   });
 *
 *   // All instances now have the .translate() method.
 *   sandbox.translate('my special message').fetch();
 *
 */
(function (ckan, $) {
  var callbacks = [];

  /* Creates a new instance of Sandbox.
   *
   * Examples
   *
   *   new Sandbox();
   *
   * Returns a new instance of Sandbox.
   */
  function Sandbox(callbacks) {
    var index = 0;
    var length = callbacks ? callbacks.length : 0;

    // Allow libraries to add objects/arrays to the sandbox object as they
    // cannot be added to the prototype without being shared.
    for (; index < length; index += 1) {
      callbacks[index](this);
    }
  }

  $.extend(Sandbox.prototype, {
    /* A scoped find function restricted to the current scope. */
    jQuery: $,

    /* An alias for jQuery.ajax() */
    ajax: $.ajax,

    body: $(document.body),

    location: window.location,

    window: window
  });

  /* Factory function for creating new sandbox instances. This should be
   * used in preference to the Sandbox constructor.
   *
   * Returns a new Sandbox instance.
   */
  function sandbox(element, options) {
    return new sandbox.Sandbox(ckan.sandbox.callbacks);
  }

  /* Allows the extension of the Sandbox prototype by other core libraries.
   *
   * NOTE: Modules should not use this.
   *
   * props - Properties/methods to add to the sandbox.
   *
   * Examples
   *
   *   ckan.sandbox.extend({
   *     translate: ckan.i18n.translate
   *   });
   *
   * Returns the ckan object.
   */
  sandbox.extend = function (props) {
    $.extend(Sandbox.prototype, props || {});
    return ckan;
  };

  /* Allows the extension of the Sandbox with objects and arrays. These
   * cannot be added to the prototype without them being shared across
   * all instances.
   *
   * fn - A callback that receives the sandbox object.
   *
   * Examples
   *
   *   ckan.sandbox.setup(function (sandbox) {
   *     sandbox.myObject = {};
   *     sandbox.myArray = [];
   *   });
   *
   * Returns the ckan object.
   */
  sandbox.setup = function setup(fn) {
    var callbacks = ckan.sandbox.callbacks = ckan.sandbox.callbacks || [];

    if (typeof fn === 'function') {
      callbacks.push(fn);
    } else {
      throw new Error('ckan.sandbox.setup() must be passed a function');
    }

    return ckan;
  };

  // Export Sandbox for testing.
  ckan.sandbox = sandbox;
  ckan.sandbox.Sandbox = Sandbox;

})(this.ckan, this.jQuery);
