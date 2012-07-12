this.ckan.module('resource-upload-field', {
  options: {
    form: {
      action: 'http://ckanext-storage.commondatastorage.googleapis.com/',
      method: 'POST',
      params: {
        'x-goog-meta-uploaded-by': 'c03155ce-8319-46ef-b4b2-4bf3303735d3'
      }
    },
    template: [
      '<span class="resource-upload-field">',
      '<i class="ckan-icon ckan-icon-link-plugin"></i>',
      '<input id="field-resource-type-file" type="file" />',
      '<label class="radio inline" for="field-resource-type-file">Upload a file</label>',
      '</span>'
    ].join('\n')
  },

  initialize: function () {
    var options = this.options;
    var upload  = this.sandbox.jQuery(options.template);

    upload.find('input').fileupload({
      url: options.form.action,
      type: options.form.method,
      forceIframeTransport: true, // Required for XDomain request. 
      replaceFileInput: false,
      autoUpload: false,
      add:  this._onUploadAdd,
      send: this._onUploadSend,
      done: this._onUploadDone,
      fail: this._onUploadFail
    });

    this.el.append(upload);
  },

  loading: function (show) {
    this.el.addClass();
  },

  notify: function (message, type) {
    var title = this.sandbox.translate('An Error Occurred').fetch();
    this.sandbox.notify(title, message, type);
  },

  _onUploadAdd: function (event, data) {
    var request = this.sandbox.client.getStorageAuth(data.files[0].name);
    request.then(function (response) {
      data.formData = response.fields;
      data.submit();
    }, this.onAuthFail);
  },

  _onUploadFail: function () {
    var _ = this.sandbox.translate;
    this.notify(_('Unable to upload file'));
  },

  _onUploadSend: function () {
    this.loading();
  },

  _onUploadDone: function (event, data) {
    this.sandbox.publish('resource:uploaded', data);
  },

  _onAuthFail: function () {
    var _ = this.sandbox.translate;
    this.notify(_('Unable to authenticate upload'));
  }
});
