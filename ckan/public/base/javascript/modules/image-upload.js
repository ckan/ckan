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
      field_name: 'name',
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

    /* Should be changed to true if user modifies resource's name
     *
     * @type {Boolean}
     */
    _nameIsDirty: false,

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
      var field_name = 'input[name="' + options.field_name + '"]';

      this.input = $(field_upload, this.el);
      this.field_url = $(field_url, this.el).parents('.control-group');
      this.field_image = this.input.parents('.control-group');
      this.field_url_input = $('input', this.field_url);
      this.field_name = this.el.parents('form').find(field_name);

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

      // Disables autoName if user modifies name field
      this.field_name
        .on('change', this._onModifyName);
      // Disables autoName if resource name already has value,
      // i.e. we on edit page
      if (this.field_name.val()){
        this._nameIsDirty = true;
      }

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
      this.field_url_input.focus()
        .on('blur', this._onFromWebBlur);
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
      this._autoName(file_name);
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
    },

    /* Event listener for changes in resource's name by direct input from user
     *
     * Returns nothing
     */
    _onModifyName: function() {
      this._nameIsDirty = true;
    },

    /* Event listener for when someone loses focus of URL field
     *
     * Returns nothing
     */
    _onFromWebBlur: function() {
      var url = this.field_url_input.val().match(/([^\/]+)\/?$/)
      if (url) {
        this._autoName(url.pop());
      }
    },

    /* Automatically add file name into field Name
     *
     * Select by attribute [name] to be on the safe side and allow to change field id
     * Returns nothing
     */
     _autoName: function(name) {
        if (!this._nameIsDirty){
          this.field_name.val(name);
        }
     }
  };
});
