/* Module for the resource form. Handles validation and updating the form
 * with external data such as from a file upload.
 */
this.ckan.module('resource-form', function (jQuery, _) {
  return {
    /* Called by the ckan core if a corresponding element is found on the page.
     * Handles setting up event listeners, adding elements to the page etc.
     *
     * Returns nothing.
     */
    initialize: function () {
      jQuery.proxyAll(this, /_on/);
      this.sandbox.subscribe('resource:uploaded', this._onResourceUploaded);
    },

    /* Remove any subscriptions to prevent memory leaks. This function is
     * called when a module element is removed from the page.
     *
     * Returns nothing..
     */
    teardown: function () {
      this.sandbox.unsubscribe('resource:uploaded', this._onResourceUploaded);
    },

    /* Callback function that loads a newly uploaded resource into the form.
     * Handles updating the various types of form fields.
     *
     * resource - A resource data object.
     *
     * Examples
     *
     *   this.sandbox.subscribe('resource:uploaded', this._onResourceUploaded);
     *
     * Returns nothing.
     */
    _onResourceUploaded: function (resource) {
      var key;
      var field;

      for (key in resource) {
        if (resource.hasOwnProperty(key)) {
          field = this.$('[name="' + key + '"]');

          if (field.is(':checkbox, :radio')) {
            this.$('[value="' + resource[key] + '"]').prop('checked', true);
          } else if (field.is('select')) {
            field.prop('selected', resource[key]);
          } else {
            field.val(resource[key]);
          }
        }
      }
    }
  };
});
