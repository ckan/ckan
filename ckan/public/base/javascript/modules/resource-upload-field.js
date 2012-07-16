/* This module creates a new resource_type field for an uploaded file and
 * appends file input into the page.
 *
 * Events:
 *
 * Publishes the 'resource:uploaded' event when a file is successfully
 * uploaded. An callbacks receive an object of resource data.
 *
 * See: http://docs.ckan.org/en/latest/filestore.html 
 *
 * options - form: General form overrides for the upload.
 *           template: Optional template can be provided.
 *
 */
this.ckan.module('resource-upload-field', function (jQuery, _, i18n) {
  return {
    /* Default options for the module */
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

    /* Initializes the module,  creates new elements and registers event
     * listeners etc. This method is called by ckan.initialize() if there
     * is a corresponding element on the page.
     *
     * Returns nothing.
     */
    initialize: function () {
      jQuery.proxyAll(this, /_on/);

      this.upload = jQuery(this.options.template);
      this.setupFileUpload();
      this.el.append(this.upload);
    },

    /* Sets up the jQuery.fileUpload() plugin with the provided options.
     *
     * Returns nothing.
     */
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

    /* Displays a loading spinner next to the input while uploading. This
     * can be cancelled by recalling the method passing false as the first
     * argument.
     *
     * show - If false hides the spinner (default: true).
     *
     * Examples
     *
     *   module.loading(); // Show spinner
     *
     *   module.loading(false); // Hide spinner.
     *
     * Returns nothing.
     */
    loading: function (show) {
      this.upload.toggleClass('loading', show);
    },

    /* Requests Authentication for the upload from CKAN. Uses the
     * _onAuthSuccess/_onAuthError callbacks.
     *
     * key  - A unique key for the file that is to be uploaded.
     * data - The file data object from the jQuery.fileUpload() plugin.
     *
     * Examples
     *
     *   onFileAdd: function (event, data) {
     *     this.authenticate('my-file', data);
     *   }
     *
     * Returns an jqXHR promise.
     */
    authenticate: function (key, data) {
      data.key = key;

      var request = this.sandbox.client.getStorageAuth(key);
      var onSuccess = jQuery.proxy(this._onAuthSuccess, this, data);
      return request.then(onSuccess, this._onAuthError);
    },

    /* Requests file metadata for the uploaded file and calls the
     * _onMetadataSuccess/_onMetadataError callbacks.
     *
     * key  - A unique key for the file that is to be uploaded.
     * data - The file data object from the jQuery.fileUpload() plugin.
     *
     * Examples
     *
     *   onFileUploaded: function (event, data) {
     *     this.lookupMetadata('my-file', data);
     *   }
     *
     * Returns an jqXHR promise.
     */
    lookupMetadata: function (key, data) {
      var request = this.sandbox.client.getStorageMetadata(key);
      var onSuccess = jQuery.proxy(this._onMetadataSuccess, this, data);
      return request.then(onSuccess, this._onMetadataError);
    },

    /* Displays a global notification for the upload status.
     *
     * message - A message string to display.
     * type    - The type of message eg. error/info/warning
     *
     * Examples
     *
     *   module.notify('Upload failed', 'error');
     *
     * Returns nothing.
     */
    notify: function (message, type) {
      var title = _('An Error Occurred').fetch();
      this.sandbox.notify(title, message, type);
    },

    /* Creates a unique key for the filename provided. This is a url
     * safe string with a timestamp prepended.
     *
     * filename - The filename for the upload.
     *
     * Examples
     *
     *   module.generateKey('my file');
     *   // => '2012-06-05T12:00:00.000Z/my-file'
     *
     * Returns a unique string.
     */
    generateKey: function (filename) {
      var parts = filename.split('.');
      var extension = jQuery.url.slugify(parts.pop());

      // Clean up the filename hopefully leaving the extension intact.
      filename = jQuery.url.slugify(parts.join('.')) + '.' + extension;
      return jQuery.date.toISOString() + '/' + filename;
    },

    /* Callback called when the jQuery file upload plugin receives a file.
     *
     * event - The jQuery event object.
     * data  - An object of file data.
     *
     * Returns nothing.
     */
    _onUploadAdd: function (event, data) {
      if (data.files && data.files.length) {
        var key = this.generateKey(data.files[0].name);

        this.authenticate(key, data);
      }
    },

    /* Callback called when the jQuery file upload plugin fails to upload
     * a file.
     */
    _onUploadFail: function () {
      this.sandbox.notify(_('Unable to upload file').fetch());
    },

    /* Callback called when jQuery file upload plugin sends a file */
    _onUploadSend: function () {
      this.loading();
    },

    /* Callback called when jQuery file upload plugin successfully uploads a file */
    _onUploadDone: function (event, data) {
      this.lookupMetadata(data.key, data);
    },

    /* Callback called when jQuery file upload plugin completes a request
     * regardless of it's success/failure.
    */
    _onUploadComplete: function () {
      this.loading(false);
    },

    /* Callback function for a successful Auth request. This cannot be
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

    /* Called when the request for auth credentials fails. */
    _onAuthError: function (event, data) {
      this.sandbox.notify(_('Unable to authenticate upload').fetch());
      this._onUploadComplete();
    },

    /* Called when the request for file metadata succeeds */
    _onMetadataSuccess: function (data, response) {
      var resource = this.sandbox.client.convertStorageMetadataToResource(response);

      this.sandbox.notify(_('Resource uploaded').fetch(), '', 'success');
      this.sandbox.publish('resource:uploaded', resource);
    },

    /* Called when the request for file metadata fails */
    _onMetadataError: function () {
      this.sandbox.notify(_('Unable to get data for uploaded file').fetch());
      this._onUploadComplete();
    }
  };
});
