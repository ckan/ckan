(function (jQuery) {
  /* Accepts a form element and once changed binds an event handler to the
   * window "beforeunload" event that warns a user that the form has unsaved
   * changes. The notice is only displayed if the user does not submit the
   * form.
   *
   * message - A message to display to the user (browser support dependant).
   *
   * Examples
   *
   *   jQuery('form').incompleteFormWarning('Form has modified fields');
   *
   * Returns the jQuery collection.
   */
  jQuery.fn.incompleteFormWarning = function (message) {
    return this.each(function () {
      var form = jQuery(this);
      var state = form.serialize();

      function onWindowUnload(event) {
        if (event.originalEvent.returnValue) {
          event.originalEvent.returnValue = message;
        }
        return message;
      }

      form.on({
        change: function () {
          // See if the form has changed, if so add an event listener otherwise
          // remove it.
          var method = form.serialize() === state ? 'off' : 'on';
          jQuery(window)[method]('beforeunload', onWindowUnload);
        },
        submit: function () {
          // Allow the form to be submitted.
          jQuery(window).off('beforeunload', onWindowUnload);
        }
      });
    });
  };
})(this.jQuery);
