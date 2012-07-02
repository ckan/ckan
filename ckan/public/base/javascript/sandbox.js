this.ckan = this.ckan || {};

(function (ckan, $) {
  // An empty jQuery object to use for event management.
  ckan.events = jQuery({});

  ckan.sandbox = function (element, options) {
    return {
      /* The jQuery element for the current module */
      el: jQuery(element),

      /* The options object passed into the module either via data-* attributes
       * or the default settings.
       */
      options: options,

      /* A scoped find function restricted to the current scope. */
      $: function (selector) {
        return this.el(selector);
      },

      /* An alias for ckan.trans() */
      trans: ckan.trans,

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
        ckan.events.triggerHandler(topic, [].slice.call(arguments, 1));
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
        ckan.events.on(topic, wrapper);
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
        ckan.events.off(this.el, arguments);
        return this;
      }
    };
  };
})(this.ckan, this.jQuery);
