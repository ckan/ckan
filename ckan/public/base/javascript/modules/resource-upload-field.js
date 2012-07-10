this.ckan.module('resource-upload-field', function (sandbox, options) {
  var upload = jQuery(options.template);

  upload.find('input').fileupload({
    // needed because we are posting to remote url
    forceIframeTransport: true,

    replaceFileInput: false,

    autoUpload: false,

    fail: function(e, data) {
      console.log(data);
    },

    add: function(e, data) {
      data.submit();
    },

    send: function(e, data) {
      console.log(data);
    },

    done: function(e, data) {
      console.log(data);
    }
  });

  sandbox.el.append(upload);
}, {
  template: [
    '<span class="resource-upload-field">',
    '<i class="ckan-icon ckan-icon-link-plugin"></i>',
    '<input id="field-resource-type-file" type="file" />',
    '<label class="radio inline" for="field-resource-type-file">Upload a file</label>',
    '</span>'
  ].join('\n')
});
