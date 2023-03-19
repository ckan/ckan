this.ckan.module('tabledesigner_datatables_buttons', function($, _) {
  return {
    initialize: function() {
      var defn = $(this)[0].el;
      var editText = defn.data('edit-text');
      var editUrl = defn.data('edit-url');

      const table = $('#dtprv').DataTable();
      table.button().add(0, {
        extend: "selectedSingle",
        text: editText,
        action: function ( e, dt, button, config ){
          var _id = dt.rows( { selected: true } ).data()[0]._id;
          window.parent.location = editUrl + '?_id=' + encodeURIComponent(_id);
        }
      });
    }
  }
});
