var run_query = function(params, format) {
  var form = $('#filtered-datatables-download');
  var p = $('<input name="params" type="hidden"/>');
  p.attr("value", JSON.stringify(params));
  form.append(p);
  var f = $('<input name="format" type="hidden"/>');
  f.attr("value", format);
  form.append(f);
  form.submit();
};

// create the yacdf column filters
function initColFiters(searchdelaysetting) {
    var dt = $('#dtprv').DataTable({retrieve: true});

    var colspecs = [];
    $('#dtprv thead tr:eq(0) th').each(function(index, item) {
        var colspec = {};
        if (index > 0) {
            var coltype = $(item).data('type');
            if (coltype === 'numeric') {
                sort_as = 'num';
            } else {
                sort_as = 'alphaNum';
            }

            colspec = {
                column_number: index,
                filter_type: 'text',
                sort_as: sort_as,
                filter_delay: searchdelaysetting,
                filter_reset_button_text: false
            };
            colspecs.push(colspec);
        }
    });

    yadcf.init(dt, colspecs);

    // we also need a small delay before 
    // force aligning header widths with column widths
    setTimeout(function() {
        var dt = $('#dtprv').DataTable({retrieve: true});
        dt.columns.adjust().draw();
    }, 300);
};

// compile active filters for display in print and clipboard copy
function filterinfo(dt, tableSearchText, colFilterText) {
    const dtinfo = document.getElementById('dtprv_info');

    var filtermsg = dtinfo.innerText;
    var tablesearch = dt.search();

    // add active filter info to messageTop
    if (tablesearch) {
        filtermsg = filtermsg + ' - <b>' + tableSearchText + ':</b> ' + tablesearch;
    }
    var colsearchflag = false;
    var colsearchmsg = '';
    dt.columns().every(function() {
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
};

// Copy link to clipboard
function copyLink(dt, deeplink, shareText, sharemsgText) {

    var hiddenDiv = $('<div/>')
        .css({
            height: 1,
            width: 1,
            overflow: 'hidden',
            position: 'fixed',
            top: 0,
            left: 0
        });

    var textarea = $('<textarea readonly/>')
        .val(deeplink)
        .appendTo(hiddenDiv);

    // use copy execCommand to copy link to clipboard
    if (document.queryCommandSupported('copy')) {
        hiddenDiv.appendTo(dt.table().container());
        textarea[0].focus();
        textarea[0].select();

        try {
            var successful = document.execCommand('copy');
            hiddenDiv.remove();

            if (successful) {
                dt.buttons.info(
                    dt.i18n('buttons.copyTitle', shareText),
                    dt.i18n('buttons.copySuccess', sharemsgText),
                    2000
                );
                return;
            }
        } catch (t) {}
    }
};

// main
this.ckan.module('datatables_view', function (jQuery) {
  return {
    initialize: function() {

      const resourcename = $('#dtprv').data('resource-name');
      var languagefile = $('#dtprv').data('languagefile');
      const statesaveflag = $('#dtprv').data('state-save-flag');
      const stateduration = $('#dtprv').data('state-duration');
      const searchdelaysetting = $('#dtprv').data('search-delay-setting');
      const resourceviewid = $('#dtprv').data('resource-view-id');
      const responsiveflag = $('#dtprv').data('responsive-flag');
      const pagelengthchoices = $('#dtprv').data('page-length-choices');
      const toppaginationcontrols = $('#dtprv').data('top-pagination-controls');
      const ajaxurl = $('#dtprv').data('ajaxurl');
      const ckanfilters = $('#dtprv').data('ckanfilters');

      // responsive mode not compatible with scrollX
      var scrollXflag = true;
      if ( responsiveflag ) {
        scrollXflag = false;
      }

      var domsettings = 'lBifrtip';
      if ( toppaginationcontrols ) {
        domsettings = 'lpBifrtip';
      }

      // labels for showing active filters in clipboard copy & print
      const tableSearchText = this._('TABLE SEARCH');
      const colFilterText = '   ' + this._('COLUMN FILTER/S');

      // labels for Sharing current view
      const shareText = this._('Share current view');
      const sharemsgText = this._('Copied deeplink to clipboard');

      // en is the default language, no need to load i18n file
      if (languagefile === '/vendor/DataTables/i18n/en.json') {
        languagefile = '';
      }

      // initialize yadcf language defaults
      yadcf.initDefaults({
          language: {
              select: this._('Select value'),
              select_multi: this._('Select values'),
              filter: this._('search'),
              range: [this._('From'), this._('To')],
              date: this._('Select a date')
          }
      });

      // init the datatable
      var datatable = $('#dtprv').DataTable({
          paging: true,
          serverSide: true,
          processing: true,
          stateSave: statesaveflag,
          stateDuration: stateduration,
          searchDelay: searchdelaysetting,
          mark: true,
          deferRender: true,
          keys: true,
          select: {
              style: "os",
              blurable: true
          },
          language: {
              url: languagefile,
              search: "&nbsp;",
              searchPlaceholder: this._('search table'),
              paginate: {
                  previous: "&lt;",
                  next: "&gt;"
              }
          },
          ajax: {
              url: ajaxurl,
              type: 'POST',
              data: {
                  "filters": ckanfilters
              }
          },
          responsive: responsiveflag,
          scrollX: scrollXflag,
          scrollY: 60,
          scrollResize: true,
          scrollCollapse: true,
          lengthMenu: pagelengthchoices,
          dom: domsettings,
          initComplete: function(settings, json) {
            initColFiters(searchdelaysetting);
          },
          stateLoadParams: function(settings, data) {
            // check the current url to see if we've got a state to restore from a deeplink
            var url = new URL(window.location.href);
            var state = url.searchParams.get("state");
            if (state) {

                // if so, try to base64 decode it and parse into object from a json
                try {
                    state = JSON.parse(atob(state));
                    // now iterate over the object properties and assign any that
                    // exist to the current loaded state (skipping "time")
                    for (var k in state) {
                        if (state.hasOwnProperty(k) && k != 'time') {
                            data[k] = state[k];
                        }
                    }
                } catch (e) {
                    console.error(e);
                }

                // doing this forces dt to access localstorage
                // ensuring the deeplink is rendered properly
                const api = new $.fn.dataTable.Api( settings );
                const dtstate = api.state.loaded();
            }
          },
          buttons: [{
              extend: "copy",
              text: '<i class="fa fa-files-o"></i>',
              titleAttr: this._('Copy to clipboard'),
              title: function() {
                var filternohtml = filterinfo(datatable, tableSearchText, colFilterText).replace( /(<([^>]+)>)/ig, '');
                return resourcename + ' - ' + filternohtml;
              }
          }, {
              extend: "colvis",
              text: '<i class="fa fa-eye-slash"></i>',
              titleAttr: this._('Toggle column visibility'),
              columns: ":gt(0)",
              collectionLayout: "fixed four-column",
              postfixButtons: [{
                  extend: "colvisRestore",
                  text: '<i class="fa fa-undo"></i> ' + this._('Restore visibility')
              }, {
                  extend: "colvisGroup",
                  text: '<i class="fa fa-eye"></i> ' + this._('Show all'),
                  show: ":hidden"
              }, {
                  extend: "colvisGroup",
                  text: '<i class="fa fa-eye-slash"></i> ' + this._('Show none'),
                  hide: ":visible"
              }]
          }, {
              text: '<i class="fa fa-download"></i>',
              titleAttr: this._('Filtered download'),
              autoClose: true,
              extend: 'collection',
              buttons: [{
                  text: 'CSV',
                  action: function(e, dt, button, config) {
                      var params = datatable.ajax.params();
                      params.visible = datatable.columns().visible().toArray();
                      run_query(params, 'csv');
                  }
              }, {
                  text: 'TSV',
                  action: function(e, dt, button, config) {
                      var params = datatable.ajax.params();
                      params.visible = datatable.columns().visible().toArray();
                      run_query(params, 'tsv');
                  }
              }, {
                  text: 'JSON',
                  action: function(e, dt, button, config) {
                      var params = datatable.ajax.params();
                      params.visible = datatable.columns().visible().toArray();
                      run_query(params, 'json');
                  }
              }, {
                  text: 'XML',
                  action: function(e, dt, button, config) {
                      var params = datatable.ajax.params();
                      params.visible = datatable.columns().visible().toArray();
                      run_query(params, 'xml');
                  }
              }]
          }, {
              text: '<i class="fa fa-repeat"></i>',
              titleAttr: this._('Reset'),
              action: function(e, dt, node, config) {
                  dt.state.clear();
                  window.location.reload();
              }
          }, {
              extend: 'print',
              text: '<i class="fa fa-print"></i>',
              titleAttr: this._('Print'),
              title: resourcename,
              messageTop: function() {
                return filterinfo(datatable, tableSearchText, colFilterText);
              }, 
              messageBottom: function() {
                return filterinfo(datatable, tableSearchText, colFilterText);
              },
              exportOptions: {
                  columns: ':visible'
              }
          }, {
              text: '<i class="fa fa-share"></i>',
              titleAttr: this._('Share current view'),
              action: function(e, dt, node, config) {
                dt.state.save();
                var sharelink = window.location.href + '?state=' + btoa(JSON.stringify(dt.state()));
                copyLink(dt, sharelink, shareText, sharemsgText);
              }
          }]
      });

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
