this.ckan.module('slug-preview-target', function (mod) {
  mod.subscribe('slug-preview-created', function (preview) {
    // Append the preview string after the target input.
    mod.el.after(preview);
  });

  // Once the preview box is modified stop watching it.
  mod.subscribe('slug-preview-modified', function () {
    mod.el.off('.slug-preview');
  });

  // Watch for updates to the target field and update the hidden slug field
  // triggering the "change" event manually.
  mod.el.on('keyup.slug-preview', function (event) {
    mod.publish('slug-target-changed', this.value);
    //slug.val(this.value).trigger('change');
  });
});

this.ckan.module('slug-preview-slug', function (mod, options, _) {
  var slug = mod.el.slug();
  var parent = slug.parents('.control-group');
  var preview;

  if (!(parent.length)) {
    return;
  }

  // Leave the slug field visible
  if (!parent.hasClass('error')) {
    preview = parent.slugPreview({
      prefix: options.prefix,
      placeholder: options.placeholder,
      i18n: {
        'Edit': _('Edit').fetch()
      }
    });

    mod.publish('slug-preview-created', preview[0]);
  }

  // Watch for updates to the target field and update the hidden slug field
  // triggering the "change" event manually.
  mod.subscribe('slug-target-changed', function (value) {
    slug.val(value).trigger('change');
  });

  // If the user manually enters text into the input we cancel the slug
  // listeners so that we don't clobber the slug when the title next changes.
  slug.keypress(function () {
    if (event.charCode) {
      mod.publish('slug-preview-modified', preview[0]);
    }
  });
}, {
  prefix: '',
  placeholder: '<slug>'
});
