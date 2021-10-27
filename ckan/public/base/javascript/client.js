(function (ckan, jQuery) {

  function Client(options) {
    this.endpoint = options && options.endpoint || '';
    jQuery.proxyAll(this, /parse/);
  }

  jQuery.extend(Client.prototype, {

    /* Creates an API url from the path provided. If a fully qualified url
     * is provided then this function just returns the input.
     *
     * path - A path to add the API domain to.
     *
     * Examples
     *
     *   client.url('/datasets'); // http://api.example.com/datasets
     *
     * Returns an url string.
     */
    url: function (path) {
      if (!(/^https?:\/\//i).test(path)) {
        path = this.endpoint + '/' + path.replace(/^\//, '');
      }
      return path;
    },

    /* Simple helper function for both GET's and POST's to the ckan API
     * 
     * type - GET or POST
     * path - The API endpoint
     * data - Any data you need passing to the endpoint
     * fn - The callback function that you want the result data passed to
     *
     * Examples
     *
     *    client.call('GET', 'user_show', { id: 'some-long-id' }, function(json) { console.log(json) })
     *
     */
    call: function(type, path, data, fn, error) {
      var url = this.url('/api/action/' + path);
      var error = ( error == 'undefined' ) ? function() {} : error;
      var options = {
        contentType: 'application/json',
        url: url,
        dataType: 'json',
        processData: false,
        success: fn,
        error: error
      };
      if (type == 'POST') {
        options.type = 'POST';
        options.data = JSON.stringify(data);
      } else {
        options.type = 'GET';
        options.url += data;
      }
      jQuery.ajax(options);
    },

    /* Requests a block of HTML from the snippet API endpoint. Optional
     * parameters can also be provided to the template via the params
     * object.
     *
     * filename - The filename of the snippet to load including extension.
     * params   - Optional query string parameters.
     * success  - A callback to be called on success. Receives the html string.
     * error    - A callback to be called on error.
     *
     * Examples
     *
     *   client.getTemplate('dataset-list.html', {limit: 5}, function (html) {
     *     // Do something with the html.
     *   });
     *
     * Returns a jqXHR promise object.
     */
    getTemplate: function (filename, params, success, error) {
      var url = this.url('/api/1/util/snippet/' + encodeURIComponent(filename));

      // Allow function to be called without params argument.
      if (typeof params === 'function') {
        error   = success;
        success = params;
        params  = {};
      }

      return jQuery.get(url, params || {}).then(success, error);
    },

    /* Fetches the current locale translation from the API.
     *
     * locale - The current page locale.
     *
     * Examples
     *
     *   var locale = jQuery('html').attr('lang');
     *   client.getLocaleData(locale, function (data) {
     *     // Load into the localizer.
     *   });
     *
     * Returns a jQuery xhr promise.
     */
    getLocaleData: function (locale, success, error) {
      var url = this.url('/api/i18n/' + (locale || ''));
      return jQuery.getJSON(url).then(success, error);
    },

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
      var request = jQuery.ajax({url: this.url(url)});

      return request.pipe(formatter).promise(request).then(success, error);
    },

    /* Takes a JSON response from an auto complete endpoint and normalises
     * the data into an array of strings. This also will remove duplicates
     * from the results (this is case insensitive).
     *
     * data    - The parsed JSON response from the server.
     * options - An object of options for the method.
     *           objects: If true returns an object of results.
     *
     * Examples
     *
     *   jQuery.getJSON(tagCompletionUrl, function (data) {
     *     var parsed = client.parseCompletions(data);
     *   });
     *
     * Returns the parsed object.
     */
    parseCompletions: function (data, options) {
      if (typeof data === 'string') {
        // Package completions are returned as a crazy string. So we handle
        // them separately.
        return this.parsePackageCompletions(data, options);
      }

      var map = {};
      // If given a 'result' array then convert it into a Result dict inside a Result dict.
      // new syntax (not used until all browsers support arrow notation):
      //data = data.result ? { 'ResultSet': { 'Result': data.result.map(x => ({'Name': x})) } } : data;
      // compatible syntax:
      data = data.result ? { 'ResultSet': { 'Result': data.result.map(function(val){ return { 'Name' :val } }) } } : data;
      // If given a Result dict inside a ResultSet dict then use the Result dict.
      var raw = jQuery.isArray(data) ? data : data.ResultSet && data.ResultSet.Result || {};

      var items = jQuery.map(raw, function (item) {
        var key = typeof options.key != 'undefined' ? item[options.key] : false;
        var label = typeof options.label != 'undefined' ? item[options.label] : false;

        let children = item.children;
        item = typeof item === 'string' ? item : item.name || item.Name || item.Format || '';
        item = jQuery.trim(item);

        key = key ? key : item;
        label = label ? label : item;

        /* Having the "ID" mark an element as selectable
           Group labels should not be selectable
           Children should include its own IDs and TEXTs
        */
        let ret = {text: label};
        if (children === undefined) {
          // This is a regular element without children
          ret.id = key;
        } else {
          // This is a group. Children need ID and TEXT
          // "key" and "label" should be defined
          for (i = 0, l = children.length; i < l; i = i + 1) {
            children[i].id = children[i][options.key];
            children[i].text = children[i][options.label];
          }
          ret.children = children;
        }

        var lowercased = item.toLowerCase();
        var returnObject = options && options.objects === true;

        if (lowercased && !map[lowercased]) {
          map[lowercased] = 1;
          return returnObject ? ret : item;
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
      return {
        results: this.parseCompletions(data, {objects: true})
      };
    },

    /* Parses the string returned by the package autocomplete endpoint which
     * is a newline separated list of packages. Each package consists of
     * a name and an id separated by a pipe (|) character.
     *
     * string - The string returned by the API.
     *
     * Returns an array of parsed packages.
     */
    parsePackageCompletions: function (string, options) {
      var packages = jQuery.trim(string).split('\n');
      var parsed = [];

      return jQuery.map(packages, function (pkg) {
        var parts = pkg.split('|');
        var id    = jQuery.trim(parts.pop() || '');
        var text  = jQuery.trim(parts.join('|') || '');
        return options && options.objects === true ? {id: id, text: text} : id;
      });
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
        url: this.url('/api/storage/auth/form/' + key),
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
        url: this.url('/api/storage/metadata/' + key),
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
      // Date constructor chokes on hyphens and timezones.
      var modified = new Date(this.normalizeTimestamp(meta._last_modified));
      var created  = new Date(this.normalizeTimestamp(meta._creation_date));

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
    },

    /* Adds a timezone to the provided timestamp if one is not present. This
     * fixes an inconsistency between Webkit and Firefox where Firefox parses
     * the date in the current users timezone but Webkit uses UTC.
     *
     * string - A timestamp string.
     *
     * Examples
     *
     *   client.normalizeTimestamp("2012-07-17T14:35:35");
     *   // => "2012-07-17T14:35:35Z"
     *
     *   client.normalizeTimestamp("2012-07-17T14:35:35+0100");
     *   // => "2012-07-17T14:35:35+0100"
     *
     * Returns a new timestamp with timezone.
     */
    normalizeTimestamp: function (string) {
      var tz = /[+\-]\d{4}|Z/;
      if (!tz.test(string)) {
        string += 'Z';
      }
      return string;
    }
  });

  ckan.sandbox.setup(function (instance) {
    instance.client = new Client({endpoint: ckan.SITE_ROOT});
  });

  ckan.Client = Client;

})(this.ckan, this.jQuery);
