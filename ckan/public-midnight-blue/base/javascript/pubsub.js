this.ckan = this.ckan || {};

/* The ckan.pubsub object allows the various components of the CKAN site
 * to talk to each other. This is primarily used by modules using the sandbox
 * object to pass messages between themselves but it may also be useful
 * for the libraries themselves to broadcast notifications.
 *
 * This implementation is built on top of the exiting jQuery event logic
 * and as such uses a pubsub.events object to manage handlers.
 */
(function (ckan, $) {
  // NOTE: These methods all use pubsub internally to refer to themself rather
  // than "this", this is to ensure access to the events object. However they
  // all return "this" so they retain the chain of the parent object.
  // eg. pubsub.publish() returns pubsub and sandbox.publish() returns sandbox.
  var pubsub = {
    /* An empty jQuery object to use for event management. */
    events: $({}),

    /* An array for holding queued items. Queue is disabled when null */
    queue: null,

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
      if (pubsub.queue) {
        pubsub.queue.push([].slice.call(arguments));
      } else {
        pubsub.events.triggerHandler(topic, [].slice.call(arguments, 1));
      }
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
        $.each(topic, $.proxy(pubsub.subscribe, this));
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
      pubsub.events.on(topic, wrapper);
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
      pubsub.events.off(topic, arguments);
      return this;
    },

    /* Starts caching all published events. After this is called no
     * subscriptions will be called until .dequeue() is called. This is useful
     * for deferring events until the page has loaded.
     *
     * Examples
     *
     *   pubsub.enqueue();
     *   jQuery.ready(pubsub.dequeue);
     *
     * Returns itself.
     */
    enqueue: function () {
      if (!pubsub.queue) {
        pubsub.queue = [];
      }
      return this;
    },

    /* Loops through each item in the queue and publishes it.
     *
     * Examples
     *
     *   if (allModulesLoaded) {
     *     pubsub.dequeue();
     *   }
     *
     * Returns itself.
     */
    dequeue: function () {
      if (pubsub.queue) {
        var queue = pubsub.queue;
        var index = 0;
        var length = queue.length;

        // We set the queue to null here to prevent events published within the
        // following loop to be added to the queue. This reduces the chances
        // of an infinite loop but does mean that events may be called out of
        // order.
        pubsub.queue = null;

        for (;index < length; index += 1) {
          pubsub.publish.apply(pubsub, queue[index]);
        }
      }
      return this;
    }
  };

  ckan.pubsub = pubsub;

  // Extend the sandbox with the pubsub methods.
  ckan.sandbox.extend({
    publish:     pubsub.publish,
    subscribe:   pubsub.subscribe,
    unsubscribe: pubsub.unsubscribe
  });

})(this.ckan, this.jQuery);
