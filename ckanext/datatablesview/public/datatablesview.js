this.ckan.module('datatables_view', function (jQuery) {
  return {
    initialize: function() {
      jQuery('#dtprv').DataTable({});
    }
  }
});
