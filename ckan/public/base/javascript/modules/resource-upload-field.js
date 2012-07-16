/* Events:
 *
 * Publishes the 'resource:uploaded' event when a file is successfully
 * uploaded. An callbacks receive an object of resource data.
 *
 * See: http://docs.ckan.org/en/latest/filestore.html 
 *
 * param - comment
 *
 * Examples
 *
 *   example
 *
 * Returns .
 */
this.ckan.module('resource-upload-field', function (jQuery, _, i18n) {
  return {
    options: {
      form: {
        method: 'POST',
        file: 'file',
        params: {
          'x-goog-meta-uploaded-by': 'c03155ce-8319-46ef-b4b2-4bf3303735d3'
        }
      },
      template: [
        '<span class="resource-upload-field">',
        '<i class="ckan-icon ckan-icon-link-plugin"></i>',
        '<input type="file" />',
        '<input id="field-resource-type-file" type="radio" name="resource_type" value="file.upload" />',
        '<label class="radio inline" for="field-resource-type-file"></label>',
        '</span>'
      ].join('\n')
    },

    initialize: function () {
      jQuery.proxyAll(this, /_on/);

      this.upload = jQuery(this.options.template);
      this.setupFileUpload();
      this.el.append(this.upload);
    },

    setupFileUpload: function () {
      var options = this.options;

      this.upload.find('label').text(_('Upload a file').fetch());
      this.upload.find('input[type=file]').fileupload({
        url: options.form.action,
        type: options.form.method,
        paramName: options.form.file,
        forceIframeTransport: true, // Required for XDomain request. 
        replaceFileInput: true,
        autoUpload: false,
        add:  this._onUploadAdd,
        send: this._onUploadSend,
        done: this._onUploadDone,
        fail: this._onUploadFail,
        always: this._onUploadComplete
      });
    },

    loading: function (show) {
      this.upload.toggleClass('loading', show);
    },

    authenticate: function (key, data) {
      data.key = key;

      var request = this.sandbox.client.getStorageAuth(key);
      var onSuccess = jQuery.proxy(this._onAuthSuccess, this, data);
      request.then(onSuccess, this._onAuthError);
    },

    lookupMetadata: function (key, data) {
      var request = this.sandbox.client.getStorageMetadata(key);
      var onSuccess = jQuery.proxy(this._onMetadataSuccess, this, data);
      request.then(onSuccess, this._onMetadataError);
    },

    notify: function (message, type) {
      var title = _('An Error Occurred').fetch();
      this.sandbox.notify(title, message, type);
    },

    generateKey: function (filename) {
      var parts = filename.split('.');
      var extension = jQuery.url.slugify(parts.pop());

      // Clean up the filename hopefully leaving the extension intact.
      filename = jQuery.url.slugify(parts.join('.')) + '.' + extension;
      return jQuery.date.toISOString() + '/' + filename;
    },

    _onUploadAdd: function (event, data) {
      if (data.files && data.files.length) {
        var key = this.generateKey(data.files[0].name);

        this.authenticate(key, data);
      }
    },

    _onUploadFail: function () {
      this.sandbox.notify(_('Unable to upload file').fetch());
    },

    _onUploadSend: function () {
      this.loading();
    },

    _onUploadDone: function (event, data) {
      this.lookupMetadata(data.key, data);
    },

    _onUploadComplete: function () {
      this.loading(false);
    },

    /* Callback function for a successfull Auth request. This cannot be
     * used straight up but requires the data object to be passed in
     * as the first argument.
     *
     * data     - The data object for the current upload.
     * response - The auth response object.
     *
     * Examples
     *
     *   var onSuccess = jQuery.proxy(this._onAuthSuccess, this, data);
     *   sandbox.client.getStorageAuth(key).done(onSuccess);
     *
     * Returns nothing.
     */
    _onAuthSuccess: function (data, response) {
      data.url = response.action;
      data.formData = response.fields;
      data.submit();
    },

    _onAuthError: function (event, data) {
      this.sandbox.notify(_('Unable to authenticate upload').fetch());
      this._onUploadComplete();
    },

    _onMetadataSuccess: function (data, response) {
      var resource = this.sandbox.client.convertStorageMetadataToResource(response);

      this.sandbox.notify(_('Resource uploaded').fetch(), '', 'success');
      this.sandbox.publish('resource:uploaded', resource);
    },

    _onMetadataError: function () {
      this.sandbox.notify(_('Unable to get data for uploaded file').fetch());
      this._onUploadComplete();
    }
  };
});
