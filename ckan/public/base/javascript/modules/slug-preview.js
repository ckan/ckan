this.ckan.module('slug-preview-target', {
  initialize: function () {
    var sandbox = this.sandbox;
    var options = this.options;
    var el = this.el;

    sandbox.subscribe('slug-preview-created', function (preview) {
      // Append the preview string after the target input.
      el.after(preview);
    });

    // Once the preview box is modified stop watching it.
    sandbox.subscribe('slug-preview-modified', function () {
      el.off('.slug-preview');
    });

    // Watch for updates to the target field and update the hidden slug field
    // triggering the "change" event manually.
    el.on('keyup.slug-preview', function (event) {
      sandbox.publish('slug-target-changed', this.value);
      //slug.val(this.value).trigger('change');
    });
  }
});

this.ckan.module('slug-preview-slug', function (jQuery, _) {
  return {
    options: {
      prefix: '',
      placeholder: '<slug>',
      i18n: {
        url:  _('URL'),
        edit: _('Edit')
      }
    },

    initialize: function () {
      var sandbox = this.sandbox;
      var options = this.options;
      var el = this.el;
      var _ = sandbox.translate;

      var slug = el.slug();
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
            'URL': this.i18n('url'),
            'Edit': this.i18n('edit')
          }
        });

        // If the user manually enters text into the input we cancel the slug
        // listeners so that we don't clobber the slug when the title next changes.
        slug.keypress(function () {
          if (event.charCode) {
            sandbox.publish('slug-preview-modified', preview[0]);
          }
        });

        sandbox.publish('slug-preview-created', preview[0]);

        // Horrible hack to make sure that IE7 rerenders the subsequent
        // DOM children correctly now that we've render the slug preview element
        // We should drop this horrible hack ASAP
        if (jQuery.browser.msie && jQuery.browser.version == '7.0') {
          jQuery('.btn').on('click', preview, function(){ 
            jQuery('.controls').ie7redraw();
          });
          preview.hide();
          setTimeout(function() {
            preview.show();
            jQuery('.controls').ie7redraw();
          }, 10);
        }
      }

      // Watch for updates to the target field and update the hidden slug field
      // triggering the "change" event manually.
      sandbox.subscribe('slug-target-changed', function (value) {
        slug.val(value).trigger('change');
      });
    }
  };
});
