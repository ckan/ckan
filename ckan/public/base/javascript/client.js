(function (ckan, jQuery) {

  function Client() {}

  jQuery.extend(Client.prototype, {

    /* Requests config options for a file upload.
     *
     * See: http://docs.ckan.org/en/latest/filestore.html
     *
     * filename - A unique id/filename for the resource.
     *
     * Examples
     *
     *   client.getStorageAuth('myfile.jpg', function (data) {
     *     data.fields;
     *   });
     *
     *   client.getStorageAuth('myfile.jpg')
     *   .done(function (data) {
     *     data.fields;
     *   })
     *   .error(function () {
     *     showError('Something Went Wrong');
     *   });
     *
     * Returns a jqXHR promise.
     */
    getStorageAuth: function (filename, success, error) {
      if (!filename) {
        throw new Error('Must be called with a filename');
      }

      return jQuery.ajax({
        url: '/api/storage/auth/form/' + filename,
        success: success,
        error: error
      });
    }
  });

  ckan.sandbox.setup(function (instance) {
    instance.client = new Client();
  });

  ckan.Client = Client;

})(this.ckan, this.jQuery);
