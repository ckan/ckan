this.ckan.module('basic-form', function (jQuery) {
  return {
    initialize: function () {
      var message = this._('There are unsaved modifications to this form');
      this.el.incompleteFormWarning(message);
    }
  };
});
