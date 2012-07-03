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
      return this.el(selector);
    },

    /* An alias for jQuery.ajax() */
    ajax: $.ajax,

    /* Publishes an event to all modules. Can be used to notify other modules
     * that an area of the site has changed.
     *
     * topic - A topic string. These are global to all modules to choose
     *         them carefully.
     * args* - All successive arguments are passed into callbacks.
     *
     * Returns the sandbox object.
     */
    publish: function (topic /* arguments */) {
      Sandbox.events.triggerHandler(topic, [].slice.call(arguments, 1));
      return this;
    },

    /* Subscribes a module to a topic. The callback will receive any
     * arguments provided by the publisher.
     *
     * topic    - The topic to subscribe to.
     * callback - A function to be called when subscribing.
     *
     * Returns this sandbox object.
     */
    subscribe: function (topic, callback) {
      if ($.isPlainObject(topic)) {
        $.each(topic, $.proxy(this.subscribe, this));
        return this;
      }

      // Call fn, stripping out the 1st argument (the event object).
      function wrapper() {
        return callback.apply(this, [].slice.call(arguments, 1));
      }

      // Add .guid property to function to allow it to be easily unbound. Note
      // that $.guid is new in jQuery 1.4+, and $.event.guid was used before.
      wrapper.guid = callback.guid = callback.guid || ($.guid += 1);

      // Bind the handler.
      Sandbox.events.on(topic, wrapper);
      return this;
    },

    /* Unsubscribes a module from a topic. If no callback is provided then
     * all handlers for that topic will be unsubscribed.
     *
     * topic    - The topic to unsubscribe from.
     * callback - An optional callback to unsubscribe.
     *
     * Returns the sandbox object.
     */
    unsubscribe: function (topic, callback) {
      Sandbox.events.off(this.el, arguments);
      return this;
    }
  });

  // An empty jQuery object to use for event management.
  Sandbox.events = $({});

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
