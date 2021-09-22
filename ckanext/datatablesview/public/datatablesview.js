var run_query = function(params, format) {
  var form = $('#filtered-datatables-download');
  var p = $('<input name="params" type="hidden"/>');
  p.attr("value", JSON.stringify(params));
  form.append(p);
  var f = $('<input name="format" type="hidden"/>');
  f.attr("value", format);
  form.append(f);
  form.submit();
}

this.ckan.module('datatables_view', function (jQuery) {
  return {
    initialize: function() {
      var datatable = jQuery('#dtprv').DataTable({});

      // Adds download dropdown to buttons menu
      datatable.button().add(2, {
        text: 'Download',
        extend: 'collection',
        buttons: [{
          text: 'CSV',
          action: function (e, dt, button, config) {
            var params = datatable.ajax.params();
            params.visible = datatable.columns().visible().toArray();
            run_query(params, 'csv');
          }
        }, {
          text: 'TSV',
          action: function (e, dt, button, config) {
            var params = datatable.ajax.params();
            params.visible = datatable.columns().visible().toArray();
            run_query(params, 'tsv');
          }
        }, {
          text: 'JSON',
          action: function (e, dt, button, config) {
            var params = datatable.ajax.params();
            params.visible = datatable.columns().visible().toArray();
            run_query(params, 'json');
          }
        }, {
          text: 'XML',
          action: function (e, dt, button, config) {
            var params = datatable.ajax.params();
            params.visible = datatable.columns().visible().toArray();
            run_query(params, 'xml');
          }
        }]
      });
    }
  }
});
