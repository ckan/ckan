/* Image Upload
 * 
 */  
this.ckan.module('image-upload', function($, _) {
  return {
    /* options object can be extended using data-module-* attributes */
    options: {
      is_url: true,
      is_upload: false,
      field_upload: 'image_upload',
      field_url: 'image_url',
      field_clear: 'clear_upload',
      upload_label: '',
      i18n: {
        upload: _('Upload'),
        url: _('Link'),
        remove: _('Remove'),
        upload_label: _('Image'),
        upload_tooltip: _('Upload a file on your computer'),
        url_tooltip: _('Link to a URL on the internet (you can also link to an API)')
      }
    },

    /* Initialises the module setting up elements and event listeners.
     *
     * Returns nothing.
     */
    initialize: function () {
      $.proxyAll(this, /_on/);
      var options = this.options;

      // firstly setup the fields
      var field_upload = 'input[name="' + options.field_upload + '"]';
      var field_url = 'input[name="' + options.field_url + '"]';
      var field_clear = 'input[name="' + options.field_clear + '"]';

      this.input = $(field_upload, this.el);
      this.field_url = $(field_url, this.el).parents('.control-group');
      this.field_image = this.input.parents('.control-group');
      this.field_url_input = $('input', this.field_url);

      // Is there a clear checkbox on the form already?
      var checkbox = $(field_clear, this.el);
      if (checkbox.length > 0) {
        options.is_upload = true;
        checkbox.parents('.control-group').remove();
      }

      // Adds the hidden clear input to the form
      this.field_clear = $('<input type="hidden" name="clear_upload">')
        .appendTo(this.el);

      // Button to set the field to be a URL
      this.button_url = $('<a href="javascript:;" class="btn"><i class="icon-globe"></i> '+this.i18n('url')+'</a>')
        .prop('title', this.i18n('url_tooltip'))
        .on('click', this._onFromWeb)
        .insertAfter(this.input);

      // Button to attach local file to the form
      this.button_upload = $('<a href="javascript:;" class="btn"><i class="icon-cloud-upload"></i>'+this.i18n('upload')+'</a>')
        .insertAfter(this.input);

      // Button for resetting the form when there is a URL set
      $('<a href="javascript:;" class="btn btn-danger btn-remove-url"><i class="icon-remove"></i></a>')
        .prop('title', this.i18n('remove'))
        .on('click', this._onRemove)
        .insertBefore(this.field_url_input);

      // Update the main label
      $('label[for="field-image-upload"]').text(options.upload_label || this.i18n('upload_label'));

      // Setup the file input
      this.input
        .on('mouseover', this._onInputMouseOver)
        .on('mouseout', this._onInputMouseOut)
        .on('change', this._onInputChange)
        .prop('title', this.i18n('upload_tooltip'))
        .css('width', this.button_upload.outerWidth());

      // Fields storage. Used in this.changeState
      this.fields = $('<i />')
        .add(this.button_upload)
        .add(this.button_url)
        .add(this.input)
        .add(this.field_url)
        .add(this.field_image);

      if (options.is_url) {
        this._showOnlyFieldUrl();
      } else if (options.is_upload) {
        this._showOnlyFieldUrl();
        this.field_url_input.prop('readonly', true);
      } else {
        this._showOnlyButtons();
      }
    },

    /* Event listener for when someone sets the field to URL mode
     *
     * Returns nothing.
     */
    _onFromWeb: function() {
      this._showOnlyFieldUrl();
      this.field_url_input.focus();
      if (this.options.is_upload) {
        this.field_clear.val('true');
      }
    },

    /* Event listener for resetting the field back to the blank state
     *
     * Returns nothing.
     */
    _onRemove: function() {
      this._showOnlyButtons();
      this.field_url_input.val('');
      this.field_url_input.prop('readonly', false);
      this.field_clear.val('true');
    },

    /* Event listener for when someone chooses a file to upload
     *
     * Returns nothing.
     */
    _onInputChange: function() {
      var file_name = this.input.val().split(/^C:\\fakepath\\/).pop();
      this.field_url_input.val(file_name);
      this.field_url_input.prop('readonly', true);
      this.field_clear.val('');
      this._showOnlyFieldUrl();
    },

    /* Show only the buttons, hiding all others
     *
     * Returns nothing.
     */
    _showOnlyButtons: function() {
      this.fields.hide();
      this.button_upload
        .add(this.field_image)
        .add(this.button_url)
        .add(this.input)
        .show();
    },

    /* Show only the URL field, hiding all others
     *
     * Returns nothing.
     */
    _showOnlyFieldUrl: function() {
      this.fields.hide();
      this.field_url.show();
    },

    /* Event listener for when a user mouseovers the hidden file input
     *
     * Returns nothing.
     */
    _onInputMouseOver: function() {
      this.button_upload.addClass('hover');
    },

    /* Event listener for when a user mouseouts the hidden file input
     *
     * Returns nothing.
     */
    _onInputMouseOut: function() {
      this.button_upload.removeClass('hover');
    }

  };
});
