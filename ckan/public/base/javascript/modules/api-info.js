/* Loads the API Info snippet into a modal dialog. Retrieves the snippet
 * url from the data-snippet-url on the module element.
 *
 * template - The url to the template to display in a modal.
 *
 * Examples
 *
 *   <a data-module="api-info" data-module-template="http://example.com/path/to/template">API</a>
 *
 */
this.ckan.module('api-info', function (jQuery) {
  return {

    /* holds the loaded lightbox */
    modal: null,

    options: {
      template: null
    },

    /* Sets up the API info module.
     *
     * Returns nothing.
     */
    initialize: function () {
      jQuery.proxyAll(this, /_on/);

      this.el.on('click', this._onClick);
      this.el.button();
    },

    /* Displays a loading message in the button. If false is provided as an
     * argument the message is reset.
     *
     * loading - Resets the message if false.
     *
     * Examples
     *
     *   module.loading();      // Show
     *   module.loading(false); // Hide
     *
     * Returns nothing.
     */
    loading: function (loading) {
      this.el.button(loading !== false ? 'loading' : 'reset');
    },

    /* Displays the API info box.
     *
     * Examples
     *
     *   module.show()
     *
     * Returns nothing.
     */
    show: function () {
      var sandbox = this.sandbox,
          module = this;

      if (this.modal) {
        return this.modal.modal('show');
      }

      this.loadTemplate().done(function (html) {
        module.modal = jQuery(html);
        module.modal.find('.modal-header :header').append('<button class="close" data-dismiss="modal">×</button>');
        module.modal.modal().appendTo(sandbox.body);
      });
    },

    /* Hides the modal.
     *
     * Examples
     *
     *   module.hide();
     *
     * Returns nothing.
     */
    hide: function () {
      if (this.modal) {
        this.modal.modal('hide');
      }
    },

    /* Loads the template and returns a promise that on complete will
     * receive the html content for the modal.
     *
     * Examples
     *
     *   module.loadTemplate().then(onSuccess, onError);
     *
     * Returns a promise instance.
     */
    loadTemplate: function () {
      if (!this.options.template) {
        this.sandbox.notify(this._('There is no API data to load for this resource'));
        return jQuery.Deferred().reject().promise();
      }

      if (!this.promise) {
        this.loading();

        // This should use sandbox.client!
        this.promise = jQuery.get(this.options.template);
        this.promise.then(this._onTemplateSuccess, this._onTemplateError);
      }
      return this.promise;
    },

    /* Event handler for clicking on the element */
    _onClick: function (event) {
      event.preventDefault();
      this.show();
    },

    /* Success handler for when the template is loaded */
    _onTemplateSuccess: function () {
      this.loading(false);
    },

    /* error handler when the template fails to load */
    _onTemplateError: function () {
      this.loading(false);
      this.sandbox.notify(this._('Failed to load data API information'));
    }
  };
});
