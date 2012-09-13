this.ckan.module('basic-form', function (jQuery, _) {
  return {
    initialize: function () {
      var message = _('There are unsaved modifications to this form').fetch();
      this.el.incompleteFormWarning(message);
    }
  };
});
