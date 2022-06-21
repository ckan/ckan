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
      let langConfig = {};
      if( this.options.lang === 'fr' ){
        langConfig = {
          url: '//cdn.datatables.net/plug-ins/1.11.3/i18n/fr_fr.json'
        };
      }
      let datatable = jQuery('#dtprv').DataTable({
        initComplete: function( _settings, _json ){
          // Adds download dropdown to buttons menu
          let tableWrapper = jQuery('#dtprv_wrapper');
          let processingContainer = jQuery(tableWrapper).find('#dtprv_processing');
          if ( processingContainer.length > 0 ){
            processingContainer.css({
              'z-index': '2',
            });
          }
          let tableInstance = jQuery(tableWrapper).find('#dtprv').DataTable();
          tableInstance.button().add(2, {
            text: ckan.i18n._('Download'),
            extend: 'collection',
            buttons: [{
              text: 'CSV',
              action: function (e, dt, button, config) {
                var params = tableInstance.ajax.params();
                params.visible = tableInstance.columns().visible().toArray();
                run_query(params, 'csv');
              }
            }, {
              text: 'TSV',
              action: function (e, dt, button, config) {
                var params = tableInstance.ajax.params();
                params.visible = tableInstance.columns().visible().toArray();
                run_query(params, 'tsv');
              }
            }, {
              text: 'JSON',
              action: function (e, dt, button, config) {
                var params = tableInstance.ajax.params();
                params.visible = tableInstance.columns().visible().toArray();
                run_query(params, 'json');
              }
            }, {
              text: 'XML',
              action: function (e, dt, button, config) {
                var params = tableInstance.ajax.params();
                params.visible = tableInstance.columns().visible().toArray();
                run_query(params, 'xml');
              }
            }]
          });
        },
        drawCallback: function( _settings ){
          // fixes "Processing..." div visualization
          let tableWrapper = jQuery('#dtprv_wrapper');
          let processingContainer = jQuery(tableWrapper).find('#dtprv_processing');
          if ( processingContainer.length > 0 ){
            processingContainer.css({
              'display': 'none',
              'z-index': '2',
            });
          }
        },
        language: langConfig,
      });
    }
  }
});
