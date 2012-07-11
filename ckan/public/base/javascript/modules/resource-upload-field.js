this.ckan.module('resource-upload-field', function (sandbox, options) {
  var upload = jQuery(options.template);



  upload.find('input').fileupload({
    url: options.form.action,

    type: options.form.method,

    // needed because we are posting to remote url
    forceIframeTransport: true,

    replaceFileInput: false,

    autoUpload: false,

    fail: function (e, data) {
      console.log(data);
    },

    add: function(e, data) {
      jQuery.ajax({
        url: '/api/storage/auth/form/' + data.files[0].name,
        success: function(response) {
          data.formData = response.fields;
          data.submit();
        },
        error: function(jqXHR, textStatus, errorThrown) {
          // TODO: more graceful error handling (e.g. of 409)
        }
      });
    },

    send: function (e, data) {
      data.url = options.form.action;
      console.log(data);
    },

    done: function (e, data) {
      console.log(data);
    }
  });

  sandbox.el.append(upload);
}, {
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
});
