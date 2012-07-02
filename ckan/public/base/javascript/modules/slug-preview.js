(function ($, __, window) {
  var target = $('#field-title');
  var slug = $('#field-name').slug();
  var override = false;
  var parent = slug.parents('.control-group');
  var preview;

  // Leave the slug field visible
  if (!parent.hasClass('error')) {
    preview = parent.slugPreview({
      prefix: 'demo.datahub.io/dataset/',
      placeholder: '<dataset>',
      trans: {
        edit: __('Edit')
      }
    });

    // Append the preview string after the target input.
    target.after(preview);
  }

  // Watch for updates to the target field and update the hidden slug field
  // triggering the "change" event manually.
  target.keyup(function (event) {
    slug.val(this.value).trigger('change');
  });

  // If the user manually enters text into the input we cancel the slug
  // listeners so that we don't clobber the slug when the title next changes.
  slug.keypress(function () {
    if (event.charCode) {
      target.off('keyup');
    }
  });
})(this.jQuery, this.ckan.trans, this);
