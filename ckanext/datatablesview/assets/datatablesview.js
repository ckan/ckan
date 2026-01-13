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
      languagecode: 'en',
      languagefile: null,
      ajaxurl: null,
      ckanfilters: null,
      responsiveFlag: false,
      pageLengthChoices: [20, 50, 100, 500, 1000],
      responsiveModal: false,
      resourceUrl: null,
      dataDictionary: null,
      editable: false,
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
  const languageCode = CKAN_MODULE.options.languagecode;
  const languageFile = CKAN_MODULE.options.languagefile;
  const ajaxURI = CKAN_MODULE.options.ajaxurl;
  const ckanFilters = CKAN_MODULE.options.ckanfilters;
  const defaultCompactView = CKAN_MODULE.options.responsiveFlag;
  const pageLengthChoices = CKAN_MODULE.options.pageLengthChoices;
  const useCompactViewModal = CKAN_MODULE.options.responsiveModal;
  const resourceURI = CKAN_MODULE.options.resourceUrl;
  const dataDictionary = CKAN_MODULE.options.dataDictionary;
  const isEditable = CKAN_MODULE.options.editable;
  const csrfTokenName = $('meta[name="csrf_field_name"]').attr('content');

  const ajaxErrorMessage = _('Error: Could not query records. Please try again.');
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
  const tableLanguage = {
    decimal: "",
    emptyTable:  '<span id="datatable-no-records">' + _('No data available in table') + '</span>',
    info: _('Showing _START_ to _END_ of _TOTAL_ entries'),
    infoEmpty: _('Showing 0 to 0 of 0 entries'),
    infoFiltered: _('(filtered from _MAX_ total entries)'),
    infoPostFix: "",
    thousands: ",",
    lengthMenu: _('_MENU_ Show number of entries'),
    loadingRecords: _('Loading...'),
    processing: "",
    search: _('Full Text Search'),
    zeroRecords: '<span id="datatable-no-records">' + _('No matching records found') + '</span>',
    paginate: {
      first: "«",
      last: "»",
      next: "›",
      previous: "‹"
    },
    aria: {
      orderable: _('Order by this column'),
      orderableReverse: _('Reverse order this column')
    }
  };
  const colOffset = 1;  // _id col
  const defaultSortOrder = [[0, "asc"]];  // _id col
  sortOrder = defaultSortOrder;

  let table;
  let tableState;
  let _savedState = window.localStorage.getItem('DataTables_dtprv_' + viewID);
  if( _savedState ){
    tableState = JSON.parse(_savedState);
  }
  let isCompactView = typeof tableState != 'undefined' && typeof tableState.compact_view != 'undefined' ? tableState.compact_view : defaultCompactView;
  let pageLength = typeof tableState != 'undefined' && typeof tableState.page_length != 'undefined' ? tableState.page_length : pageLengthChoices[0];

  let availableColumns = [{
    data: '_id',
    name: '_id',
    searchable: false,
    type: 'num',
    className: 'dt-body-right datatable-id-col',
    width: isCompactView ? '28px' : '50px',
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

  function cell_renderer(_data, _type, _row, _meta, _dictionary_field){
    if( _type == 'display' ){
      if( _data == null ){
        // TODO: handle configed blank cell value...
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
        _data = displayList;
      }
      if( _data === true ){
        _data = 'TRUE';
      }
      if( _data === false ){
        _data = 'FALSE';
      }
      if( numberTypes.includes(_dictionary_field.type) ){
        // TODO: add number format configs/options
        _data = DataTable.render.number(null, null, null, null).display(_data, _type, _row);
      }
      // TODO: add money formatting??
      if( dateTypes.includes(_dictionary_field.type) ){
        if( ! _data.toString().includes('+0000') ){
          _data = _data.toString() + '+0000';  // add UTC offset if not present
        }
        // TODO: use configed date format
        // TODO: add locale date configs/options
        _data = new Date(_data).toLocaleString(localeString, {timeZone: "America/Montreal"}) + ' ' + timezoneString;
      }
      _data = DataTable.render.ellipsis(ellipsisLength, _meta.row, _dictionary_field.id)(_data, _type, _row, _meta);
      return _data;
    }
    return _data;
  }

  function get_available_buttons(){
    let availableButtons = [];

    availableButtons.push({
      name: 'viewToggleButton',
      text: isCompactView ? '<i class="fa fa-table"></i>' : '<i class="fa fa-list"></i>',
      titleAttr: _('Table/List toggle'),
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
        tableState.selected = table.rows({ selected: true })[0];
        // TODO: need to save more stuff to local var???
        set_state_change_visibility();
        dt.clear().destroy();
        initialize_datatable();
      }
    });

    // FIXME: copy button not working
    availableButtons.push({
      extend: 'copy',
      text: '<i class="fa fa-copy"></i>',
      titleAttr: _('Copy to clipboard'),
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
    });

    availableButtons.push({
      extend: 'colvis',
      text: '<i class="fa fa-eye-slash"></i>',
      titleAttr: _('Toggle column visibility'),
      className: 'btn-secondary',
      columns: 'th:gt(0)',
      collectionLayout: 'fixed',
      postfixButtons: [
        {
          extend: 'colvisRestore',
          text: '<i class="fa fa-undo"></i> ' + _('Restore visibility')
        },
        {
          extend: 'colvisGroup',
          text: '<i class="fa fa-eye"></i> ' + _('Show all'),
          show: ':hidden'
        },
        {
          extend: 'colvisGroup',
          text: '<i class="fa fa-eye-slash"></i> ' + _('Show none'),
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
          text: '<i class="fa fa-filter"></i> ' + _('Filtered'),
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
    });

    availableButtons.push({
      text: '<i class="fa fa-download"></i>',
      titleAttr: _('Filtered download'),
      className: 'btn-secondary',
      autoClose: true,
      extend: 'collection',
      buttons: [{
        text: 'CSV',
        action: function (e, dt, button, config) {
          let params = dt.ajax.params();
          params.visible = dt.columns().visible().toArray();
          // TODO: execute promise
          // run_query(params, 'csv');
        }
      }, {
        text: 'TSV',
        action: function (e, dt, button, config) {
          let params = dt.ajax.params();
          params.visible = dt.columns().visible().toArray();
          // TODO: execute promise
          // run_query(params, 'tsv');
        }
      }, {
        text: 'JSON',
        action: function (e, dt, button, config) {
          let params = dt.ajax.params();
          params.visible = dt.columns().visible().toArray();
          // TODO: execute promise
          // run_query(params, 'json');
        }
      }, {
        text: 'XML',
        action: function (e, dt, button, config) {
          let params = dt.ajax.params();
          params.visible = dt.columns().visible().toArray();
          // TODO: execute promise
          // run_query(params, 'xml');
        }
      }]
    });

    availableButtons.push({
      name: 'resetButton',
      text: '<i class="fa fa-repeat"></i>',
      titleAttr: _('Reset'),
      className: 'btn-secondary resetButton',
      action: function (e, dt, node, config) {
        set_state_change_visibility();
        dt.state.clear();
        dt.clear().destroy();
        initialize_datatable();
      }
    });

    availableButtons.push({
      extend: 'print',
      text: '<i class="fa fa-print"></i>',
      titleAttr: _('Print'),
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
    });

    availableButtons.push({
      name: 'shareButton',
      text: '<i class="fa fa-share"></i>',
      titleAttr: _('Share current view'),
      className: 'btn-secondary',
      action: function (e, dt, node, config) {
        dt.state.save();
        let sharelink = window.location.href + '?state=' + window.btoa(JSON.stringify(dt.state()));
        // TODO: do copy state link stuffs...
        // copyLink(dt, sharelink, that._('Share current view'), that._('Copied deeplink to clipboard'));
      }
    });

    return availableButtons;
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
    // set_button_states();
  }

  function init_callback(){
    set_table_visibility();
    // render_table_footer();
    // set_row_selects();
    // set_button_states();
  }

  function initialize_datatable(){
    let languageSettings = {
      url: languageFile,
      paginate: {
        previous: '&lt;',
        next: '&gt;',
      },
    }
    if( languageCode == 'en' ){
      languageSettings = tableLanguage;
    }

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
      searchHighlight: true,
      order: sortOrder,
      columns: availableColumns,
      dom: "Blfrtip",
      lengthMenu: pageLengthChoices,
      language: languageSettings,
      ajax: {
        "url": ajaxURI,
        "type": "POST",
        timeout: 60000, // TODO: make configurable...
        "data": function(_data){
          if( ckanFilters != null ){
            _data.filters = ckanFilters;
          }
        },
        "headers": {
          'X-CSRF-Token': $('meta[name="' + csrfTokenName + '"]').attr('content')
        },
        "complete": function(_data){
          if( _data.responseJSON ){
            if( ! _data.responseJSON.data ){
              render_ajax_failure('DataTables error - ' + _data.status + ': ' + _data.statusText);
            }
          }else{
            render_ajax_failure('DataTables error - ' + _data.status + ': ' + _data.statusText);
          }
        }
      },
      initComplete: init_callback,
      drawCallback: draw_callback,
      fnStateSave: function(_settings, _data){
        // custom local storage name for multiple table views and fullscreen views
        window.localStorage.setItem('DataTables_dtprv_' + viewID, JSON.stringify(_data));
      },
      fnStateLoad: function(_settings){
        return JSON.parse(window.localStorage.getItem('DataTables_dtprv_' + viewID));
      },
      stateSaveParams: function(_settings, _data){
        _data.page_number = this.api().page();
        _data.page_length = this.api().page.len();
        _data.selected = this.api().rows({selected: true})[0];
        _data.compact_view = isCompactView;
        let localInstanceState = typeof tableState != 'undefined' ? tableState : _data;
        tableState = _data;
        tableState.page_number = localInstanceState.page_number;
        tableState.page_length = localInstanceState.page_length;
        tableState.selected = localInstanceState.selected;
        tableState.compact_view = localInstanceState.compact_view;

        // TODO: reset button control
      },
      stateLoadParams: function(_settings, _data){
        let localInstanceState = typeof tableState != 'undefined' ? tableState : _data;
        tableState = _data;
        tableState.page_number = localInstanceState.page_number;
        tableState.page_length = localInstanceState.page_length;
        tableState.selected = localInstanceState.selected;
        tableState.compact_view = localInstanceState.compact_view;

        // TODO: check URL params for base64 decode...
      },
      buttons: get_available_buttons(),
    });
  }

  initialize_datatable();
}