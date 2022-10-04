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

var ga_event_tracking = function() {
  var location_url = encodeURIComponent(window.location);
  if (location_url) {
    var url_parse = jQuery(location).prop('pathname').split('/');
    if (url_parse) {
      ga('send', {
        hitType: 'event',
        eventCategory: 'resource',
        eventAction: 'download',
        eventLabel: location_url,
        dimension1: url_parse[jQuery.inArray( "resource", url_parse ) + 1],
        dimension2: url_parse[jQuery.inArray( "dataset", url_parse ) + 1],
      });
    }
  }
};

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
              className: 'resource-url-analytics',
              attr: {
                  'data-gc-analytics': "manualDownload",
              },
              action: function (e, dt, button, config) {
                var params = tableInstance.ajax.params();
                params.visible = tableInstance.columns().visible().toArray();
                run_query(params, 'csv');
                ga_event_tracking();
              }
            }, {
              text: 'TSV',
              className: 'resource-url-analytics',
              attr: {
                  'data-gc-analytics': "manualDownload",
              },
              action: function (e, dt, button, config) {
                var params = tableInstance.ajax.params();
                params.visible = tableInstance.columns().visible().toArray();
                run_query(params, 'tsv');
                ga_event_tracking();
              }
            }, {
              text: 'JSON',
              className: 'resource-url-analytics',
              attr: {
                  'data-gc-analytics': "manualDownload",
              },
              action: function (e, dt, button, config) {
                var params = tableInstance.ajax.params();
                params.visible = tableInstance.columns().visible().toArray();
                run_query(params, 'json');
                ga_event_tracking();
              }
            }, {
              text: 'XML',
              className: 'resource-url-analytics',
              attr: {
                  'data-gc-analytics': "manualDownload",
              },
              action: function (e, dt, button, config) {
                var params = tableInstance.ajax.params();
                params.visible = tableInstance.columns().visible().toArray();
                run_query(params, 'xml');
                ga_event_tracking();
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
