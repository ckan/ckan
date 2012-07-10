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

  /* Creates a new instance of Sandbox.
   *
   * element - An element that the sandbox is bound to.
   * options - An object of key/value pairs.
   *
   * Examples
   *
   *   new Sandbox(element, {a: 1, b: 2, c: 3});
   *
   * Returns a new instance of Sandbox.
   */
  function Sandbox(element, options) {
    this.el = element instanceof $ ? element : $(element);
    this.options = options || {};
  }

  $.extend(Sandbox.prototype, {
    /* The jQuery element for the current module */
    el: null,

    /* The options object passed into the module either via data-* attributes
     * or the default settings.
     */
    options: null,

    /* A scoped find function restricted to the current scope. */
    $: function (selector) {
      return this.el.find(selector);
    },

    /* An alias for jQuery.ajax() */
    ajax: $.ajax,
  });

  /* Factory function for creating new sandbox instances. This should be
   * used in preference to the Sandbox constructor.
   *
   * Returns a new Sandbox instance.
   */
  ckan.sandbox = function (element, options) {
    return new Sandbox(element, options);
  };

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
  ckan.sandbox.extend = function (props) {
    $.extend(Sandbox.prototype, props || {});
    return ckan;
  };

  // Export Sandbox for testing.
  ckan.sandbox.Sandbox = Sandbox;

})(this.ckan, this.jQuery);
