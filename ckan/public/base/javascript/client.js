(function (ckan, jQuery) {

  function Client() {
    jQuery.proxyAll(this, /parse/);
  }

  jQuery.extend(Client.prototype, {

    /* Retrieves a list of auto-completions from one of the various endpoints
     * and normalises the results into an array of tags.
     *
     * url     - An API endpoint for the auto complete.
     * options - An object of options for the function (optional).
     *           formatter: A function that takes the response and parses it.
     * success - A function to be called on success (optional).
     * error   - A function to be called on error (optional).
     *
     * Examples
     *
     *   client.getCompletions(tagEndpoint).done(function (tags) {
     *     // tags == array of formatted tags.
     *   });
     *
     * Returns a jqXHR promise object.
     */
    getCompletions: function (url, options, success, error) {
      if (typeof options === 'function') {
        error = success;
        success = options;
        options = {};
      }

      var formatter = options && options.format || this.parseCompletions;
      var request = jQuery.ajax({url: url});

      return request.pipe(formatter).promise(request).then(success, error);
    },

    /* Takes a JSON response from an auto complete endpoint and normalises
     * the data into an array of strings. This also will remove duplicates
     * from the results (this is case insensitive).
     *
     * data - The parsed JSON response from the server.
     *
     * Examples
     *
     *   jQuery.getJSON(tagCompletionUrl, function (data) {
     *     var parsed = client.parseCompletions(data);
     *   });
     *
     * Returns the parsed object.
     */
    parseCompletions: function (data) {
      var map = {};
      var raw = data.ResultSet && data.ResultSet.Result || {};

      var items = jQuery.map(raw, function (item) {
        item = typeof item === 'string' ? item : item.Name || item.Format || '';
        item = jQuery.trim(item);

        var lowercased = item.toLowerCase();

        if (lowercased && !map[lowercased]) {
          map[lowercased] = 1;
          return item;
        }

        return null;
      });

      // Remove duplicates.
      items = jQuery.grep(items, function (item) { return item !== null; });

      return items;
    },

    /* Returns each item as an object with an "id" and "text" property as this
     * format is used by a number of auto complete plugins.
     *
     * data - The parsed JSON response from the server.
     *
     * Example
     *
     *   var opts = {format: client.parseCompletionsForPlugin};
     *   client.getCompletions(tagEndpoint, opts).done(function (tags) {
     *     // tags    == {results: [{...}, {...}, {...}}
     *     // tags[0] == {id: "string", text: "string"}
     *   });
     *
     * Returns an object of item objects.
     */
    parseCompletionsForPlugin: function (data) {
      var items = this.parseCompletions(data);

      items = jQuery.map(items, function (item) {
        return {id: item, text: item};
      });

      return {results: items};
    },

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
      var created = new Date(meta._creation_date);

      var createdISO  = jQuery.date.toCKANString(created);
      var modifiedISO = jQuery.date.toCKANString(modified);

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
        created: createdISO,
        last_modified: modifiedISO,
        format: format,
        mimetype: meta._format || null,
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
