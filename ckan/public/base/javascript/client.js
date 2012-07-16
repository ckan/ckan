(function (ckan, jQuery) {

  function Client() {}

  jQuery.extend(Client.prototype, {

    /* Requests config options for a file upload.
     *
     * See: http://docs.ckan.org/en/latest/filestore.html
     *
     * key     - A unique id/filename for the resource.
     * success - A callback to be called on successful response.
     * error   - A callback to be called when the request fails.
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
    getStorageAuth: function (key, success, error) {
      if (!key) {
        throw new Error('Client#getStorageAuth() must be called with a key');
      }

      return jQuery.ajax({
        url: '/api/storage/auth/form/' + key,
        success: success,
        error: error
      });
    },

    /* Requests metadata for a file upload.
     *
     * See: http://docs.ckan.org/en/latest/filestore.html
     *
     * key     - A unique id/filename for the resource.
     * success - A callback to be called on successful response.
     * error   - A callback to be called when the request fails.
     *
     * Examples
     *
     *   client.getStorageMetadata('myfile.jpg', function (data) {
     *     data._format;
     *   });
     *
     * Returns a jqXHR promise.
     */
    getStorageMetadata: function (key, success, error) {
      if (!key) {
        throw new Error('Client#getStorageMetadata() must be called with a key');
      }

      return jQuery.ajax({
        url: '/api/storage/metadata/' + key,
        success: success,
        error: error
      });
    },

    /* Converts the data returned from the storage metadata into keys that
     * can be used with a dataset.
     *
     * key  - The key for the stored file.
     * meta - The metadata object.
     *
     * Examples
     *
     *   client.getStorageMetadata('myfile.jpg', function (data) {
     *     var dataset = client.convertStorageMetadataToResource(data);
     *   });
     *
     * Returns an object of dataset keys.
     */
    convertStorageMetadataToResource: function (meta) {
      var modified = new Date(meta._last_modified);
      var modifiedISO = jQuery.date.toISOString(modified);
      var filename = meta['filename-original'] || meta.key;
      var format = meta._format || filename.split('.').pop();
      var url = meta._location;

      // If this is a local upload then the returned url will not have a domain
      // and we should add one.
      if (url.indexOf('://') === -1) {
        url = ckan.url(url);
      }

      return {
        url: url,
        key: meta.key, /* Not strictly Resource data but may be useful */
        name: filename,
        size: meta._content_length,
        last_modified: modifiedISO,
        format: format,
        mimetype: format,
        resource_type: 'file.upload', // Is this standard?
        owner: meta['uploaded-by'],
        hash: meta._checksum,
        cache_url: meta._location,
        cache_url_updated: modifiedISO
      };
    }
  });

  ckan.sandbox.setup(function (instance) {
    instance.client = new Client();
  });

  ckan.Client = Client;

})(this.ckan, this.jQuery);
