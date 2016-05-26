/**
 * Data-upload module
 *
 * This module provides the user experience for adding data to a resource
 *
 * Based on image-upload.js
 *
 * Author: Jared Smith @ Highway Three Solutions
 */
this.ckan.module('data-upload', function($, _) {
  return {
    is_url: false,
    is_upload: false,
    field_url: '',
    field_upload: '',
    field_clear: '',
    options: {
      i18n: {
        upload: _('Upload'),
        url: _('Link'),
        remove: _('Remove'),
        label: _('Data'),
        label_for_url: _('URL'),
        label_for_upload: _('File'),
        upload_tooltip: _('Upload a file on your computer'),
        url_tooltip: _('Link to a URL on the internet (you can also link to an API)')
      }
    },

    initialize: function () {
      $.proxyAll(this, /_on/);
      var options = this.options;

      // firstly setup the fields
      var field_upload = 'input[name="' + options.field_upload + '"]';
      var field_url    = 'input[name="' + options.field_url    + '"]';
      var field_clear  = 'input[name="' + options.field_clear  + '"]';

      this.input               = $(field_upload, this.el);
      this.field_data          = this.input.parents('.control-group');
      this.field_url           = $(field_url, this.el).parents('.control-group');
      this.field_url_input     = $('input', this.field_url);
      this.label_data_location = $('label[for="field-data-url"]');

      // Is there a clear checkbox on the form already?
      var checkbox = $(field_clear, this.el);
      if (checkbox.length > 0) {
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
        .prop('title', this.i18n('upload_tooltip'))
        .insertAfter(this.input);

      // Button for resetting the form when there is a URL set
      $('<a href="javascript:;" class="btn btn-danger btn-remove-data">Remove</a>')
        .prop('title', this.i18n('remove'))
        .on('click', this._onRemove)
        .insertBefore(this.field_url_input);

      // Update the main label
      $('label[for="field-data-upload"]').text(this.i18n('label'));

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
        .add(this.field_data);

      if (options.is_url) {
        this._showOnlyFieldUrl();

        this.label_data_location.text(this.i18n('label_for_url'));
      }
      else if (options.is_upload) {
        this._showOnlyFieldUrl();

        this.field_url_input.prop('readonly', true);
        // If the data is an uploaded file, the filename will display rather than whole url of the site
        var filename = this._fileNameFromUpload(this.field_url_input.val());
        this.field_url_input.val(filename);

        this.label_data_location.text(this.i18n('label_for_upload'));
      }
      else {
        this._showOnlyButtons();
      }
    },

    /* Quick way of getting just the filename in the uri of the resource data
     *
     * Returns String.
     */
    _fileNameFromUpload: function(url) {
      url = url.substring(0, (url.indexOf("#") == -1) ? url.length : url.indexOf("#"));
      url = url.substring(0, (url.indexOf("?") == -1) ? url.length : url.indexOf("?"));
      url = url.substring(url.lastIndexOf("/") + 1, url.length);

      return url;
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

        this.label_data_location.text(this.i18n('label_for_url'));
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

      this.label_data_location.text(this.i18n('label_for_upload'));

      this._showOnlyFieldUrl();
    },

    /* Show only the buttons, hiding all others
     *
     * Returns nothing.
     */
    _showOnlyButtons: function() {
      this.fields.hide();
      this.button_upload
        .add(this.field_data)
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
