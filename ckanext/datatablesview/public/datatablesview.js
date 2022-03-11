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
      let langCode = this.options.lang;
      let module = this;
      let datatable = jQuery('#dtprv').DataTable({
        initComplete: function( _settings, _json ){
          // Adds download dropdown to buttons menu
          let tableInstance = jQuery('#dtprv').DataTable();
          tableInstance.button().add(2, {
            text: module._('Download'),
            extend: 'collection',
            buttons: [{
              text: module._('CSV'),
              action: function (e, dt, button, config) {
                var params = tableInstance.ajax.params();
                params.visible = tableInstance.columns().visible().toArray();
                run_query(params, 'csv');
              }
            }, {
              text: module._('TSV'),
              action: function (e, dt, button, config) {
                var params = tableInstance.ajax.params();
                params.visible = tableInstance.columns().visible().toArray();
                run_query(params, 'tsv');
              }
            }, {
              text: module._('JSON'),
              action: function (e, dt, button, config) {
                var params = tableInstance.ajax.params();
                params.visible = tableInstance.columns().visible().toArray();
                run_query(params, 'json');
              }
            }, {
              text: module._('XML'),
              action: function (e, dt, button, config) {
                var params = tableInstance.ajax.params();
                params.visible = tableInstance.columns().visible().toArray();
                run_query(params, 'xml');
              }
            }]
          });
        },
        language: function(){
          if (langCode === 'fr') {
            return {
              url: '//cdn.datatables.net/plug-ins/1.11.3/i18n/fr_fr.json'
            };
          }
          return {};
        }
      });
    }
  }
});
