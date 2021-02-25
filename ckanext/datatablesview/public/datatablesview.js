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

      var datatable = $('#dtprv').DataTable({ "retrieve": true});
      var printTitle = $('#dtprv').data('caption');
      var tableSearchText = this._('TABLE SEARCH');
      var colFilterText = this._('COLUMN FILTER/S');

      // Adds download dropdown to buttons menu
      datatable.button().add(2, {
        text: '<i class="fa fa-download"></i>',
        titleAttr: this._('Filtered download'),
        autoClose: true,
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

      // add reset button
      // resets filters and saved state
      datatable.button().add(null, {
          text: '<i class=\"fa fa-repeat\"></i>',
          titleAttr: this._('Reset'),
          action: function(e, dt, node, config) {
              datatable.state.clear();
              window.location.reload();
          }
      });

      // add print button
      datatable.button().add(null, {
          extend: 'print',
          text: '<i class=\"fa fa-print\"></i>',
          titleAttr: this._('Print'),
          title: printTitle,
          messageTop: function() {
              const dtinfo = document.getElementById('dtprv_info');
              var filtermsg = dtinfo.innerText;
              var tablesearch = datatable.search();

              // add active filter info to messageTop
              if (tablesearch) {
                  filtermsg = filtermsg + ' - <b>' + tableSearchText + ':</b> ' + tablesearch;
              }
              var colsearchflag = false;
              var colsearchmsg = '';
              datatable.columns().every(function() {
                  var colsearch = this.search();
                  var colname = this.name();

                  if (colsearch) {
                      colsearchflag = true;
                      colsearchmsg = colsearchmsg + ' <b>' + colname + ':</b> ' + colsearch + ', ';
                  }
              });
              if (colsearchflag) {
                  filtermsg = filtermsg + '</br><b>' + colFilterText + ' - </b>' + colsearchmsg.slice(0, -2);
              }
              return filtermsg;
          },
          messageBottom: function() {
              const dtinfo = document.getElementById('dtprv_info');
              return dtinfo.innerText;
          },
          exportOptions: {
              columns: ':visible',
              format: {
                  header: function(mDataProp, columnIdx) {
                      var htmlText = '<span>' + mDataProp + '</span>';
                      var jHtmlObject = jQuery(htmlText);
                      jHtmlObject.find('div').remove();
                      var newHtml = jHtmlObject.text();
                      console.log('My header > ' + newHtml);
                      return newHtml;
                  }
              }
          }
      });

      // add reset button to global search, like column filters
      $("#dtprv_filter").append('<button id="dtprv_searchreset" class="yacdf-filter-reset-button " type="button" onclick="var dt=$(\'#dtprv\').DataTable();dt.search(\'\').draw();"><b>x</b></button>');

      // create column filters
      var colspecs = [];
      var search_delay = $('#dtprv').data('search_delay');
      $('th').each(function(index, item) {
          var colspec = {};
          if (index > 0) {
              var coltype = $(item).data('type');
              if (coltype === 'numeric') {
                  sort_as = 'num';
              } else {
                  sort_as = 'alphaNum';
              }

              colspec = {
                  "column_number": index,
                  "filter_type": "text",
                  "sort_as": sort_as,
                  "filter_delay": search_delay
              };
              colspecs.push(colspec);
          }
      });
      yadcf.init(datatable, colspecs);
  }
 }
});

// register column.name() datatables API helper using data-attributes
// used by print to show active column filters
$.fn.dataTable.Api.registerPlural( 'columns().names()', 'column().name()', function ( setter ) {
    return this.iterator( 'column', function ( settings, column ) {
        var col = settings.aoColumns[column];
 
        if ( setter !== undefined ) {
            col.sName = setter;
            return this;
        }
        else {
            return col.sName;
        }
    }, 1 );
} );

// shake animation
function animateEl(element, animation, complete) {
    if (!element instanceof jQuery || !$(element).length || !animation) return null;

    if (element.data('animating')) {
        element.removeClass(element.data('animating')).data('animating', null);
        element.data('animationTimeout') && clearTimeout(element.data('animationTimeout'));
    }

    element.addClass('animated-' + animation).data('animating', 'animated-' + animation);
    element.data('animationTimeout', setTimeout((function() {
        element.removeClass(element.data('animating')).data('animating', null);
        complete && complete();
    }), 400));
}

// custom error handler instead of default datatable alert error
// this often happens when invalid datastore_search queries are returned
$.fn.dataTable.ext.errMode = 'none';
$('#dtprv').on('error.dt', function(e, settings, techNote, message) {
    console.log('DataTables error: ', message);

    // if error code 7, most probably an FTS query error. shake input
    if (techNote == 7) {
        const shake_element = $(":focus");
        animateEl(shake_element, 'shake');
    }
})
