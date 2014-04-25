this.ckan.module('basic-form', function (jQuery, _) {
  return {
    initialize: function () {
      var message = _('There are unsaved modifications to this form').fetch();
      this.el.incompleteFormWarning(message);
      this.el.on('click', '[data-type="submit"]', this._onSubmitElementClick);

      // Internet Explorer 7 fix for forms with
      this._setupFormSubmitCallbackOnIE7();
    },

    /* Event listener for when user clicks on secondaries elements that have
     * attribute [data-type="submit"]
     *
     * Returns nothing.
     */
    _onSubmitElementClick: function() {
      var button = $(this);
      var form = button.closest('form');
      $('<input type="hidden">').prop('name', button.data('name')).prop('value', button.data('value')).appendTo(form);
      form.submit();
    },

    /* Setup callback for form submission in IE7 as fallback
     * due <button type="submit"> not be working.
     *
     * Returns nothing.
     */
    _setupFormSubmitCallbackOnIE7: function() {
      if ($('html').hasClass('ie7')) {
        this.el.on('submit', function() {
          var form = $(this);
          $('button', form).each(function() {
            var button = $(this);
            $('<input type="hidden">').prop('name', button.prop('name')).prop('value', button.val()).appendTo(form);
          });
        });
      }
    }
  };
});
