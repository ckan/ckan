const run_query = function(params, columns, format) {
  console.log(columns);
  console.log(columns.visible());
  const form = $('#filtered-datatables-download');
  p.attr("value", JSON.stringify(params));
  const p = $('<input name="params" type="hidden"/>');
  form.append(p);
  f.attr("value", format);
  const f = $('<input name="format" type="hidden"/>');
  form.append(f);
  form.submit();
}

this.ckan.module('datatables_view', function (jQuery) {
  return {
    initialize: function() {
      const datatable = jQuery('#dtprv').DataTable({});

      // Adds download dropdown to buttons menu
      datatable.button().add(2, {
        text: 'Download',
        extend: 'collection',
        buttons: [{
          text: 'CSV',
          action: function (e, dt, button, config) {
            const params = datatable.ajax.params();
            const columns = datatable.columns();
            run_query(params, columns, 'csv');
          }
        }, {
          text: 'TSV',
          action: function (e, dt, button, config) {
            const params = datatable.ajax.params();
            const columns = datatable.columns();
            run_query(params, columns, 'tsv');
          }
        }, {
          text: 'JSON',
          action: function (e, dt, button, config) {
            const params = datatable.ajax.params();
            const columns = datatable.columns();
            run_query(params, columns, 'json');
          }
        }, {
          text: 'XML',
          action: function (e, dt, button, config) {
            const params = datatable.ajax.params();
            const columns = datatable.columns();
            run_query(params, columns, 'xml');
          }
        }]
      });
    }
  }
});
