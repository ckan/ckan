this.ckan.module('datatables_view', function($){
  return {
    options : {
      stateSaveFlag: true,
      stateDuration: 7200,
      ellipsisLength: 100,
      dateFormat: 'llll',
      packageName: null,
      resourceName: null,
      viewId: null,
      languageCode: 'en',
      languageObject: null,
      ajaxUrl: null,
      ckanFilters: null,
      responsiveFlag: false,
      pageLengthChoices: [20, 50, 100, 500, 1000],
      responsiveModal: false,
      resourceUrl: null,
      dataDictionary: null,
      editable: false,
      timeout: 60000,
    },
    initialize: function(){
      load_datatable(this);
    }
  }
});

function load_datatable(CKAN_MODULE){
  const _ = CKAN_MODULE._;
  const searchParams = new URLSearchParams(document.location.search);
  const doStateSave = CKAN_MODULE.options.stateSaveFlag;
  const stateSaveDuration = CKAN_MODULE.options.stateDuration;
  const ellipsisLength = CKAN_MODULE.options.ellipsisLength;
  const dateFormat = CKAN_MODULE.options.dateFormat;
  const packageName = CKAN_MODULE.options.packageName;
  const resourceName = CKAN_MODULE.options.resourceName;
  const viewID = CKAN_MODULE.options.viewId;
  const languageCode = CKAN_MODULE.options.languageCode;
  const tableLanguage = CKAN_MODULE.options.languageObject;
  const ajaxURI = CKAN_MODULE.options.ajaxUrl;
  const ckanFilters = CKAN_MODULE.options.ckanFilters;
  const defaultCompactView = CKAN_MODULE.options.responsiveFlag;
  const pageLengthChoices = CKAN_MODULE.options.pageLengthChoices;
  const useCompactViewModal = CKAN_MODULE.options.responsiveModal;
  const resourceURI = CKAN_MODULE.options.resourceUrl;
  const dataDictionary = CKAN_MODULE.options.dataDictionary;
  const isEditable = CKAN_MODULE.options.editable;
  const requestTimeout = CKAN_MODULE.options.timeout;
  const csrfTokenName = $('meta[name="csrf_field_name"]').attr('content');

  const ajaxErrorMessage = _('Error: Could not query records. Please try again.');
  const downloadFileErrorMessage = _('Error: Could not download rows to {TYPE} file. Please try again.');
  const fullTableButtonLabel = _('Full Table');
  const compactTableButtonLabel = _('Compact Table');
  const copyButtonLabel = _('Copy to clipboard');
  const colvisButtonLabel = _('Toggle column visibility');
  const colvisRestoreLabel = _('Restore visibility');
  const colvisAllLabel = _('Show all');
  const colvisNoneLabel = _('Show none');
  const colvisFilteredLabel = _('Filtered');
  const downloadButtonLabel = _('Filtered download');
  const resetButtonLabel = _('Reset');
  const printButtonLabel = _('Print');
  const shareButtonLabel = _('Share current view');
  const readLessLabel = _('less');
  const colSearchLabel = _('Search:');
  const colSortLabel = _('Sorting by:');
  const colSortAscLabel = _('Ascending');
  const colSortDescLabel = _('Descending');
  const colSortAnyLabel = _('Any');
  const numberTypes = [
    'year',
    'month',
    'int',
    'int8',
    'int16',
    'bigint',
    'numeric',
    'float',
    'double',
    'money'
  ];
  const alphaTypes = [
    'text',
    '_text'
  ];
  const dateTypes = [
    'timestamp'
  ]
  const colOffset = 1;  // _id col
  const defaultSortOrder = [[0, "asc"]];  // _id col

  let table;
  let tableState;
  let _savedState = window.localStorage.getItem('DataTables_dtprv_' + viewID);
  if( _savedState ){
    tableState = JSON.parse(_savedState);
  }
  let isCompactView = typeof tableState != 'undefined' && typeof tableState.compact_view != 'undefined' ? tableState.compact_view : defaultCompactView;
  let pageLength = typeof tableState != 'undefined' && typeof tableState.page_length != 'undefined' ? tableState.page_length : pageLengthChoices[0];
  let sortOrder = typeof tableState != 'undefined' && typeof tableState.sort_order != 'undefined' ? tableState.sort_order : defaultSortOrder;

  let availableColumns = [{
    "name": '_id',
    "data": '_id',
    "searchable": false,
    "type": 'num',
    "className": 'dt-body-right datatable-id-col',
    "width": isCompactView ? '28px' : '50px',
  }];

  for( let i = 0; i < dataDictionary.length; i++ ){
    availableColumns.push({
      "name": dataDictionary[i].id,
      "data": dataDictionary[i].id,
      "searchable": true,
      "render": function(_data, _type, _row, _meta){
        return cell_renderer(_data, _type, _row, _meta, dataDictionary[i]);
      }
    });
  }

  DataTable.ext.errMode = function( _settings, _techNote, _message ){
    // console log errors instead of window.alert
    console.warn(_message);
  };

  DataTable.Api.registerPlural('columns().names()', 'column().name()', function(_setter){
    // register column.name() DataTables API helper so we can refer
    // to columns by name instead of just column index number
    // FIXME: is it possible to have multiple columns of the same name??? PROBABLY in psql right???
    return this.iterator('column', function (_settings, _column) {
      let col = _settings.aoColumns[_column]
      if( _setter !== undefined ){
        col.sName = _setter
        return this
      }else{
        return col.sName
      }
    }, 1)
  })

  DataTable.render.ellipsis = function(_cutoff, _rowIndex, _datatoreID){
    return function(_data, _type, _row, _meta){
      if( _type == 'display' ){
        let str = _data.toString();
        let htmlStr = $($.parseHTML(str)).text();
        if( str.length < _cutoff || htmlStr.length < _cutoff ){
          return _data;
        }
        let _elementID = 'datatableReadMore_' + _rowIndex + '_' + _datatoreID;
        let expander = '<a class="datatable-readmore-expander" href="javascript:void(0);" data-toggle="collapse" data-bs-toggle="collapse" aria-expanded="false" aria-controls="' + _elementID + '">&#8230;</a>';
        let preview = str.substr(0, _cutoff - 1) + expander;
        let remaining = str.substr(_cutoff - 1);
        return '<div class="datatable-readmore"><span>' + preview + '</span><span class="collapse" id="' + _elementID + '">' + remaining + '<a class="datatable-readmore-minimizer" href="javascript:void(0);" data-toggle="collapse" data-bs-toggle="collapse" aria-expanded="true" aria-controls="' + _elementID + '"><small>[' + readLessLabel + ']</small></a><span></div>';
      }
      return _data;
    };
  };

  function download_filtered_file(_params, _format) {
    let form = $('#filtered-datatables-download');
    let p = $('<input name="params" type="hidden"/>');
    p.attr('value', JSON.stringify(_params));
    form.append(p);
    let f = $('<input name="format" type="hidden"/>');
    f.attr('value', _format);
    form.append(f);
    form.submit();
    p.remove();
    f.remove();
  }

  function cell_renderer(_data, _type, _row, _meta, _dictionary_field){
    if( typeof _row.DT_RowId != 'undefined' && _row.DT_RowId == 'dt-row-histogram' ){
      // TODO: render historgams here...
      return;
    }
    if( _type == 'display' ){
      if( _data == null ){
        return '';  // blank cell for None/null values
      }
      if( _dictionary_field.type == '_text' ){
        if( ! Array.isArray(_data) ){
          _data = _data.toString().split(',');  // split to Array if not already
        }
        let displayList = '<ul class="text-left">';
        _data.forEach(function(_val, _i, _arr){
          displayList += '<li>' + _val + '</li>';
        });
        displayList += '</ul>';
        return displayList;
      }
      if( _data === true ){
        return 'TRUE';
      }
      if( _data === false ){
        return 'FALSE';
      }
      if( numberTypes.includes(_dictionary_field.type) ){
        // TODO: add number format configs/options ??
        // number(THOUSAND, DECIMAL, PRECISION, PREFIX, POSTFIX)
        return DataTable.render.number(null, null, 2, null, null).display(_data, _type, _row);
      }
      // TODO: add money formatting ??
      if( dateTypes.includes(_dictionary_field.type) ){
        if( ! _data.toString().includes('+0000') ){
          _data = _data.toString() + '+0000';  // add UTC offset if not present
        }
        return DataTable.render.moment(window.moment.ISO_8601, dateFormat, languageCode)(_data, _type, _row, _meta);
      }
      return DataTable.render.ellipsis(ellipsisLength, _meta.row, _dictionary_field.id)(_data, _type, _row, _meta);
    }
    return _data;
  }

  function get_available_buttons(){
    return [
      {
        name: 'viewToggleButton',
        text: isCompactView ? '<i class="fa fa-table"></i>' : '<i class="fa fa-list"></i>',
        titleAttr: isCompactView ? fullTableButtonLabel : compactTableButtonLabel,
        className: 'btn-secondary',
        action: function(e, dt, node, config){
          if( isCompactView ){
            dt.button('viewToggleButton:name').text('<i class="fa fa-table"></i>');
            isCompactView = false;
            tableState.compact_view = false;
          } else {
            dt.button('viewToggleButton:name').text('<i class="fa fa-list"></i>');
            isCompactView = true;
            tableState.compact_view = true;
          }
          dt.state.save();
          set_state_change_visibility();
          dt.clear().destroy();
          initialize_datatable();
        }
      },
      {
        extend: 'copy',
        text: '<i class="fa fa-copy"></i>',
        titleAttr: copyButtonLabel,
        className: 'btn-secondary',
        title: function(){
          // const filternohtml = filterInfo(datatable, true)
          // TODO: better filterInfo...
          return resourceName;
        },
        exportOptions: {
          rows: ':not(#dt-row-histogram)',
          columns: ':visible',
          orthogonal: 'filter'
        }
      },
      {
        extend: 'colvis',
        text: '<i class="fa fa-eye-slash"></i>',
        titleAttr: colvisButtonLabel,
        className: 'btn-secondary',
        columns: 'th:gt(0)',
        collectionLayout: 'fixed dt-popup-colvis',
        postfixButtons: [
          {
            extend: 'colvisRestore',
            text: '<i class="fa fa-undo"></i> ' + colvisRestoreLabel,
          },
          {
            extend: 'colvisGroup',
            text: '<i class="fa fa-eye"></i> ' + colvisAllLabel,
            show: ':hidden'
          },
          {
            extend: 'colvisGroup',
            text: '<i class="fa fa-eye-slash"></i> ' + colvisNoneLabel,
            action: function(e, dt, node, config){
              dt.columns().every(function(){
                if( this.index() ){ // always show _id col, index 0
                  this.visible(false);
                }
              });
            }
          },
          {
            extend: 'colvisGroup',
            text: '<i class="fa fa-filter"></i> ' + colvisFilteredLabel,
            action: function(e, dt, node, config){
              dt.columns().every(function(){
                if( this.index() ){  // always show _id col, index 0
                  if( this.search() ){
                    this.visible(true);
                  }else{
                    this.visible(false);
                  }
                }
              });
            }
          }
        ]
      },
      {
        text: '<i class="fa fa-download"></i>',
        titleAttr: downloadButtonLabel,
        className: 'btn-secondary',
        autoClose: true,
        extend: 'collection',
        buttons: [{
          text: 'CSV',
          action: function (e, dt, button, config) {
            let params = dt.ajax.params();
            params.visible = dt.columns().visible().toArray();
            download_filtered_file(params, 'csv');
          }
        }, {
          text: 'TSV',
          action: function (e, dt, button, config) {
            let params = dt.ajax.params();
            params.visible = dt.columns().visible().toArray();
            download_filtered_file(params, 'tsv');
          }
        }, {
          text: 'JSON',
          action: function (e, dt, button, config) {
            let params = dt.ajax.params();
            params.visible = dt.columns().visible().toArray();
            download_filtered_file(params, 'json');
          }
        }, {
          text: 'XML',
          action: function (e, dt, button, config) {
            let params = dt.ajax.params();
            params.visible = dt.columns().visible().toArray();
            download_filtered_file(params, 'xml');
          }
        }]
      },
      {
        name: 'resetButton',
        text: '<i class="fa fa-repeat"></i>',
        titleAttr: resetButtonLabel,
        className: 'btn-secondary disabled resetButton',
        action: function (e, dt, node, config) {
          set_state_change_visibility();
          if( $('.dt-buttons button.resetButton').hasClass('btn-warning') ){
            $('.dt-buttons button.resetButton').removeClass('btn-warning').addClass('btn-secondary');
          }
          dt.state.clear();
          dt.clear().destroy();
          initialize_datatable();
        }
      },
      {
        extend: 'print',
        text: '<i class="fa fa-print"></i>',
        titleAttr: printButtonLabel,
        className: 'btn-secondary',
        title: packageName + ' — ' + resourceName,
        messageTop: function () {
          return 'TODO: better filterInfo';
          // return filterInfo(datatable);
        },
        messageBottom: function () {
          return 'TODO: better filterInfo';
          // return filterInfo(datatable)
        },
        exportOptions: {
          columns: ':visible',
          stripHtml: false
        }
      },
      {
        name: 'shareButton',
        text: '<i class="fa fa-share"></i>',
        titleAttr: shareButtonLabel,
        className: 'btn-secondary',
        action: function (e, dt, node, config) {
          dt.state.save();
          let sharelink = window.location.href + '?state=' + window.btoa(JSON.stringify(dt.state()));
          // TODO: do copy state link stuffs...
          // copyLink(dt, sharelink, that._('Share current view'), that._('Copied deeplink to clipboard'));
        }
      }
    ];
  }

  function _render_failure(_consoleMessage, _message, _type){
    console.warn(_consoleMessage);
    table.processing(false);
    $('#dtprv_processing').css({'display': 'none'});
    $('#dtprv_wrapper').find('#dtprv_failure_message').remove();
    $('#dtprv_wrapper').find('.dt-scroll').before('<div id="dtprv_failure_message" class="alert alert-dismissible show alert-' + _type + '"><p>' + _message + '</p></div>');
  }

  function render_ajax_failure(_message){
    _render_failure(_message, ajaxErrorMessage, 'warning');
  }

  function render_download_file_failure(_message, _format){
    _render_failure(_message, downloadFileErrorMessage.replace('{TYPE}', _format), 'warning');
  }

  function set_row_selects(){
    if( typeof tableState != 'undefined' && typeof tableState.selected != 'undefined' ){
      table.rows(tableState.selected).select();
    }
  }

  function set_table_visibility(){
    $('#dtprv').css({'visibility': 'visible'});
    $('table.dataTable').css({'visibility': 'visible'});
    $('.dt-scroll-head').css({'visibility': 'visible'});
    $('.dt-scroll-head').find('th.expanders').css({'visibility': 'visible'});
    $('.dt-length').css({'visibility': 'visible'});
    $('.dt-search').css({'visibility': 'visible'});
    $('#dtprv-editor-button').css({'visibility': 'visible'});
    $('#dtprv-editor-button').find('button').css({'display': 'flex'});
    $('#dtprv_wrapper').attr('data-editable', isEditable);
    $('#dtprv_wrapper').attr('data-compact-view', isCompactView);
    $('#dtprv_wrapper').find('tr').children('th:first-of-type').css(
      {'width': 'auto', 'min-width': 'auto', 'max-width': 'auto', 'padding': '8px',  'visibility': 'visible'});
    $('#dtprv_wrapper').find('tr').children('td:first-of-type').css(
      {'width': 'auto', 'min-width': 'auto', 'max-width': 'auto', 'padding': '8px',  'visibility': 'visible'});
  }

  function set_state_change_visibility(){
    $('#dtprv').css({'visibility': 'hidden'});
    $('.dt-scroll-head').css({'visibility': 'hidden'});
    $('.dt-scroll-head').find('th.expanders').css({'visibility': 'hidden'});
    $('.dt-length').css({'visibility': 'hidden'});
    $('.dt-search').css({'visibility': 'hidden'});
    $('#dtprv-editor-button').css({'visibility': 'hidden'});
    $('#dtprv-editor-button').find('button').css({'display': 'none'});
  }

  function draw_callback(_settings){
    $('#dtprv_wrapper').find('#dtprv_failure_message').remove();
    set_table_visibility();
    // render_expand_buttons();
    // render_human_sorting();
  }

  function init_callback(){
    set_table_visibility();
    // render_table_footer();
    set_row_selects();
  }

  function initialize_datatable(){
    table = $('#dtprv').DataTable({
      paging: true,
      serverSide: true,
      processing: true,
      responsive: isCompactView,
      autoWidth: true,
      stateSave: doStateSave,
      stateDuration: stateSaveDuration,
      colReorder: {
        fixedColumnsLeft: 1
      },
      fixedColumns: ! isCompactView,
      orderCellsTop: true,
      mark: true,
      select: {
        style: 'os',
        blurable: true,
        selector: 'tr:not(#dt-row-histogram)'
      },
      scrollX: ! isCompactView,
      scrollY: 400,
      scrollResize: true,
      scrollCollapse: false,
      deferRender: true,
      pageLength: pageLength,
      search: {
        return: true,
      },
      searching: true,
      mark: true,
      order: sortOrder,
      columns: availableColumns,
      dom: "Blfrtip",
      lengthMenu: pageLengthChoices,
      language: tableLanguage,
      ajax: {
        "url": ajaxURI,
        "type": "POST",
        "timeout": requestTimeout,
        "data": function(_data){
          if( ckanFilters != null ){
            _data.filters = ckanFilters;
          }
        },
        "headers": {
          'X-CSRF-Token': $('meta[name="' + csrfTokenName + '"]').attr('content'),
        },
        "complete": function(_data){
          if( _data.responseJSON ){
            if( ! _data.responseJSON.data ){
              render_ajax_failure('DataTables error - ' + _data.status + ': ' + _data.statusText);
            }
            console.log(_data.responseJSON);
          }else{
            render_ajax_failure('DataTables error - ' + _data.status + ': ' + _data.statusText);
          }
        }
      },
      initComplete: init_callback,
      drawCallback: draw_callback,
      fnStateSave: function(_settings, _data){
        if( ! doStateSave ){
          return;
        }
        // custom local storage name for multiple table views and fullscreen views
        window.localStorage.setItem('DataTables_dtprv_' + viewID, JSON.stringify(_data));
      },
      fnStateLoad: function(_settings){
        if( ! doStateSave ){
          return;
        }
        return JSON.parse(window.localStorage.getItem('DataTables_dtprv_' + viewID));
      },
      stateSaveParams: function(_settings, _data){
        if( ! doStateSave ){
          return;
        }

        _data.page_number = this.api().page();
        _data.page_length = this.api().page.len();
        _data.selected = this.api().rows({selected: true})[0];
        _data.sort_order = this.api().order();
        _data.compact_view = isCompactView;

        let localInstanceState = typeof tableState != 'undefined' ? tableState : _data;
        tableState = _data;

        tableState.page_number = localInstanceState.page_number;
        tableState.page_length = localInstanceState.page_length;
        tableState.selected = localInstanceState.selected;
        tableState.sort_order = localInstanceState.sort_order;
        tableState.compact_view = localInstanceState.compact_view;

        $('.dt-buttons button.resetButton').removeClass('btn-secondary').removeClass('disabled').addClass('btn-warning');
        // TODO: reset button control
        // if( typeof tableState != 'undefined' && tableState != _data ){
        //   $('.dt-buttons button.resetButton').removeClass('btn-secondary').removeClass('disabled').addClass('btn-warning');
        // }else{
        //   $('.dt-buttons button.resetButton').removeClass('btn-warning').addClass('btn-secondary').addClass('disabled');
        // }
      },
      stateLoadParams: function(_settings, _data){
        if( ! doStateSave ){
          return;
        }

        let localInstanceState = typeof tableState != 'undefined' ? tableState : _data;
        tableState = _data;

        tableState.page_number = localInstanceState.page_number;
        tableState.page_length = localInstanceState.page_length;
        tableState.selected = localInstanceState.selected;
        tableState.sort_order = localInstanceState.sort_order;
        tableState.compact_view = localInstanceState.compact_view;

        // TODO: check URL params for base64 decode...
      },
      buttons: get_available_buttons(),
    });
  }

  initialize_datatable();
}