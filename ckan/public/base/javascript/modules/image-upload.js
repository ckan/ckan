/* Image Upload
 * 
 *
 * Options
 * - id: what's the id of the context?
 */  
this.ckan.module('image-upload', function($, _) {
  return {
    /* options object can be extended using data-module-* attributes */
    options: {
      is_url: true,
      has_image: false,
      i18n: {
        upload: _('From computer'),
        url: _('From web'),
        remove: _('Remove'),
        label: _('Upload image'),
        label_url: _('Image URL'),
        remove_tooltip: _('Reset this')
      },
      template: [
        ''
      ].join("\n")
    },

    state: {
      attached: 1,
      blank: 2,
      web: 3
    },

    /* Initialises the module setting up elements and event listeners.
     *
     * Returns nothing.
     */
    initialize: function () {
      $.proxyAll(this, /_on/);
      var options = this.options;

      // firstly setup the fields
      this.input = $('input[name="image_upload"]', this.el);
      this.field_url = $('input[name="image_url"]', this.el).parents('.control-group');
      this.field_image = this.input.parents('.control-group');

      var checkbox = $('input[name="clear_upload"]', this.el);
      if (checkbox.length > 0) {
        options.has_image = true;
        checkbox.parents('.control-group').remove();
      }

      this.field_clear = $('<input type="hidden" name="clear_upload">')
        .appendTo(this.el);

      this.button_url = $('<a href="javascript:;" class="btn"><i class="icon-globe"></i> '+this.i18n('url')+'</a>')
        .on('click', this._onFromWeb)
        .insertAfter(this.input);

      this.button_upload = $('<a href="javascript:;" class="btn"><i class="icon-cloud-upload"></i>'+this.i18n('upload')+'</a>')
        .insertAfter(this.input);

      this.button_remove = $('<a href="javascript:;" class="btn btn-danger" />')
        .text(this.i18n('remove'))
        .on('click', this._onRemove)
        .insertAfter(this.button_upload);

      $('<a href="javascript:;" class="btn btn-danger btn-remove-url"><i class="icon-remove"></i></a>')
        .prop('title', this.i18n('remove_tooltip'))
        .on('click', this._onRemove)
        .insertBefore($('input', this.field_url));

      $('label[for="field-image-upload"]').text(this.i18n('label'));

      this.input
        .on('mouseover', this._onInputMouseOver)
        .on('mouseout', this._onInputMouseOut)
        .on('change', this._onInputChange)
        .css('width', this.button_upload.outerWidth())
        .hide();

      this.fields = $('<i />')
        .add(this.button_remove)
        .add(this.button_upload)
        .add(this.button_url)
        .add(this.input)
        .add(this.field_url)
        .add(this.field_image);

      if (options.is_url) {
        this.changeState(this.state.web);
      } else if (options.has_image) {
        this.changeState(this.state.attached);
      } else {
        this.changeState(this.state.blank);
      }

    },

    changeState: function(state) {
      this.fields.hide();
      if (state == this.state.blank) {
        this.button_upload
          .add(this.field_image)
          .add(this.button_url)
          .add(this.input)
          .show();
      } else if (state == this.state.attached) {
        this.button_remove
          .add(this.field_image)
          .show();
      } else if (state == this.state.web) {
        this.field_url
          .show();
      }
    },

    _onFromWeb: function() {
      this.changeState(this.state.web);
      $('input', this.field_url).focus();
      if (this.options.has_image) {
        this.field_clear.val('true');
      }
    },

    _onRemove: function() {
      this.changeState(this.state.blank);
      $('input', this.field_url).val('');
      if (this.options.has_image) {
        this.field_clear.val('true');
      }
    },

    _onInputChange: function() {
      this.file_name = this.input.val();
      this.field_clear.val('');
      this.changeState(this.state.attached);
    },

    _onInputMouseOver: function() {
      this.button_upload.addClass('hover');
    },

    _onInputMouseOut: function() {
      this.button_upload.removeClass('hover');
    }

  }
});
