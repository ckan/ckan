(function (ckan, jQuery) {

  /* Displays a global notification banner on the screen. Takes a title
   * and optional message and type arguments.
   *
   * title   - The main message string.
   * message - Additional information.
   * type    - A type to apply to the message (default: error)
   *
   * Examples
   *
   *   ckan.notify('An error occurred', 'etc');
   *   ckan.notify('Success', 'user updated', 'success');
   *
   *   var alert = ckan.notify('An error occurred');
   *   alert.on('closed', function () {
   *     // Do something.
   *   });
   *
   * Returns the error element.
   */
  function notify(title, message, type) {
    var alert = notify.initialize(notify.create(title, message, type));
    notify.el.append(alert);
  }

  // Grab the flash message container.
  notify.el = jQuery('.flash-messages', document.body);

  /* Creates a new message element.
   *
   * title   - The main message string.
   * message - Additional information.
   * type    - A type to apply to the message (default: error)
   *
   * Returns the element.
   */
  notify.create = function (title, message, type) {
    var alert = jQuery('<div class="alert fade in"><strong></strong> <span></span></div>');
    alert.addClass('alert-' + (type || 'error'));
    alert.find('strong').text(title);
    alert.find('span').text(message);
    return alert;
  };

  /* Adds a close button and initializes the Bootstrap alert plugin.
   *
   * element - An element to initialize.
   *
   * Returns the element.
   */
  notify.initialize = function (element) {
    element = element instanceof jQuery ? element : jQuery(element);
    return element.append(jQuery('<a class="close" href="#">&times;</a>')).alert();
  };

  // Initialize any alerts already on the page.
  notify.el.find('.alert').each(function () {
    notify.initialize(this);
  });

  // Watch for close clicks and remove the alert.
  notify.el.on('click', '.close', function () {
    jQuery(this).parent().alert('close');
  });

  // Export the objects.
  ckan.notify = notify;
  ckan.sandbox.extend({notify: notify});

})(this.ckan, this.jQuery);
