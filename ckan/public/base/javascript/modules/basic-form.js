this.ckan.module('basic-form', function (jQuery, _) {
  return {
    initialize: function () {
      var message = _('There are unsaved modifications to this form').fetch();
      this.el.incompleteFormWarning(message);

      this.el.on('click', '[data-type="submit"]', this._onSubmitElementClick);

      // Internet Explorer 7 fix for forms with <button type="submit">
      if ($('html').hasClass('ie7')) {
        this.el.on('submit', this._onFormSubmit);
      }
    },

    /* Event listener for when user clicks on secondaries elements that have
     * attribute data-type="submit"
     *
     * Returns nothing.
     */
    _onSubmitElementClick: function() {
      var button = $(this);
      var form = button.closest('form');
      $('<input type="hidden">').prop('name', button.data('name')).prop('value', button.data('value')).appendTo(form);
      form.submit();
    },

    /* Event listener for when form is submitted and user is using IE7
     * as you can see at line 9
     *
     * Returns nothing.
     */
    _onFormSubmit: function() {
      var form = $(this);
      $('button', form).each(function() {
        var button = $(this);
        $('<input type="hidden">').prop('name', button.prop('name')).prop('value', button.val()).appendTo(form);
      });
    }
  };
});
