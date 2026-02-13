this.ckan.module('datatables_view', function($){
  return {
    options : {
      stateSaveFlag: true,
      stateDuration: 7200,
      ellipsisLength: 100,
      dateFormat: 'llll',
      packageName: null,
      resourceName: null,
      createdDate: null,
      dataUpdatedDate: null,
      metadataUpdatedDate: null,
      resourceFormat: null,
      resourceFileSize: null,
      resourceFileSizeHumanized: null,
      viewId: null,
      languageCode: 'en',
      languageObject: null,
      ajaxUrl: null,
      ckanFilters: null,
      responsiveFlag: false,
      pageLengthChoices: [20, 50, 100, 500, 1000],
      resourceUrl: null,
      dataDictionary: null,
      editable: false,
      timeout: 60000,
    },
    initialize: function(){
      /**
       * Call functional code so we can destory and re-initialize the objects
       * we need to, instead of the entire module object (or requiring page reload).
       */
      load_datatable(this);
    }
  }
});

function _clean_for_html_attr(_v){
  /**
   * Cleans passed value to be used in HTML attributes.
   */
  _v = _v.toLowerCase();
  // Make alphanumeric (removes all other characters)
  _v = _v.replace(/[^a-z0-9_\s-]/g, '');
  // Convert whitespaces and underscore to #
  _v = _v.replace(/[\s_]/g, '#');
  // Convert multiple # to hyphen
  _v = _v.replace(/[#]+/g, '-');
  return _v
}

function _escape_html(_v){
  /**
   * Escape basic HTML tagging characters.
   */
  return _v.replace(/&/g, '&amp;')
           .replace(/</g, '&lt;')
           .replace(/>/g, '&gt;')
           .replace(/"/g, '&quot;');
}

function _download_filtered_file(_params, _format) {
  /**
   * Execute the form POST to download the Filtered DataStore Dump file.
   */
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

function load_datatable(CKAN_MODULE){
  const _ = CKAN_MODULE._;
  const searchParams = new URLSearchParams(document.location.search);
  const doStateSave = CKAN_MODULE.options.stateSaveFlag;
  const stateSaveDuration = CKAN_MODULE.options.stateDuration;
  const ellipsisLength = CKAN_MODULE.options.ellipsisLength;
  const dateFormat = CKAN_MODULE.options.dateFormat;
  const packageName = CKAN_MODULE.options.packageName;
  const resourceName = CKAN_MODULE.options.resourceName;
  const createdDate = CKAN_MODULE.options.createdDate;
  const dataUpdatedDate = CKAN_MODULE.options.dataUpdatedDate;
  const metadataUpdatedDate = CKAN_MODULE.options.metadataUpdatedDate;
  const resourceFormat = CKAN_MODULE.options.resourceFormat;
  const resourceFileSize = CKAN_MODULE.options.resourceFileSize;
  const resourceFileSizeHumanized = CKAN_MODULE.options.resourceFileSizeHumanized;
  const viewID = CKAN_MODULE.options.viewId;
  const languageCode = CKAN_MODULE.options.languageCode;
  const tableLanguage = CKAN_MODULE.options.languageObject;
  const ajaxURI = CKAN_MODULE.options.ajaxUrl;
  const ckanFilters = CKAN_MODULE.options.ckanFilters;
  const defaultCompactView = CKAN_MODULE.options.responsiveFlag;
  const pageLengthChoices = CKAN_MODULE.options.pageLengthChoices;
  const resourceURI = CKAN_MODULE.options.resourceUrl;
  const dataDictionary = CKAN_MODULE.options.dataDictionary;
  const isEditable = CKAN_MODULE.options.editable;
  const requestTimeout = CKAN_MODULE.options.timeout;
  const csrfTokenName = $('meta[name="csrf_field_name"]').attr('content');

  const ajaxErrorMessage = _('Error: Could not query records. Please try again.');
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
  const estimatedLabel = _('Total was estimated');
  const exactLabel = _('Total is exact');
  const elapsedTimeLabel = _('seconds');
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
  let ajaxStartTime = 0;
  let ajaxElapsedTime;

  let keyedDataDictionary = {};
  let table;
  let tableState;
  let _savedState = window.localStorage.getItem('DataTables_dtprv_' + viewID);
  if( _savedState ){
    tableState = JSON.parse(_savedState);
  }
  let isCompactView = typeof tableState != 'undefined' && typeof tableState.compact_view != 'undefined' ? tableState.compact_view : defaultCompactView;
  let pageLength = typeof tableState != 'undefined' && typeof tableState.page_length != 'undefined' ? tableState.page_length : pageLengthChoices[0];
  let sortOrder = typeof tableState != 'undefined' && typeof tableState.sort_order != 'undefined' ? tableState.sort_order : defaultSortOrder;
  let didEstimatedTotal;

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
    // use id for key so we can get info easier
    keyedDataDictionary[dataDictionary[i].id] = dataDictionary[i];
  }

  DataTable.ext.errMode = function( _settings, _techNote, _message ){
    /**
     * Console log all DataTable errors instead of the default window.alert
     */
    console.warn(_message);
  };

  DataTable.Api.registerPlural('columns().names()', 'column().name()', function(_setter){
    /**
     * Register a Plural for DataTables so we can refer to columns by
     * names (DataStore IDs) instead of just column index number.
     */
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
    /**
     * Custom DataTable render function for ellipsis.
     */
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

  DataTable.ColumnControl.SearchInput.prototype.runSearch = function(){
    /**
     * NOTE: ColumnControl plugin does not have options for searching on
     *       ENTER keypress. Override the method here, and call column.search()
     *       on ENTER keypress in our custom event handlers.
     */
    return;
  }

  function _get_translated(_obj, _key){
    /**
     * Get the value of a possibly translated object
     */
    if( typeof _obj[_key] == 'undefined' ){
      return null;
    }
    if( typeof _obj[_key + '_' + languageCode] != 'undefined' ){
      return _obj[_key + '_' + languageCode];
    }
    if( typeof _obj[_key][languageCode] != 'undefined' ){
      return _obj[_key][languageCode];
    }
    return _obj[_key];
  }

  function cell_renderer(_data, _type, _row, _meta, _dictionary_field){
    /**
     * Our custom Cell renderer for all cells in the table.
     */
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
    /**
     * Get buttons available to the DataTable.
     *
     * NOTE: this is done in a function so the table view mode can change faster & better.
     */
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
            _download_filtered_file(params, 'csv');
          }
        }, {
          text: 'TSV',
          action: function (e, dt, button, config) {
            let params = dt.ajax.params();
            params.visible = dt.columns().visible().toArray();
            _download_filtered_file(params, 'tsv');
          }
        }, {
          text: 'JSON',
          action: function (e, dt, button, config) {
            let params = dt.ajax.params();
            params.visible = dt.columns().visible().toArray();
            _download_filtered_file(params, 'json');
          }
        }, {
          text: 'XML',
          action: function (e, dt, button, config) {
            let params = dt.ajax.params();
            params.visible = dt.columns().visible().toArray();
            _download_filtered_file(params, 'xml');
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
          if( ! defaultCompactView ){
            dt.button('viewToggleButton:name').text('<i class="fa fa-table"></i>');
            isCompactView = false;
            tableState.compact_view = false;
          } else {
            dt.button('viewToggleButton:name').text('<i class="fa fa-list"></i>');
            isCompactView = true;
            tableState.compact_view = true;
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
      // FIXME: Base64ing the entire table state is way too large.
      //        We could add normal URI params for the only required things
      //        like "sort, col_filters, query, compact, page, length";
      //        However, we cannot reliably add column reordering,
      //        column visibility, and view filters to the URI as they can
      //        be almost infinite for a URI. Network middlewares and proxies
      //        may also set max lengths and parameters, so those would break.
      // {
      //   name: 'shareButton',
      //   text: '<i class="fa fa-share"></i>',
      //   titleAttr: shareButtonLabel,
      //   className: 'btn-secondary',
      //   action: function (e, dt, node, config) {
      //     dt.state.save();
      //     let sharelink = window.location.href + '?state=' + window.btoa(JSON.stringify(dt.state()));
      //   }
      // }
    ];
  }

  function _render_failure(_consoleMessage, _message, _type){
    /**
     * Render UI alert at the top of the table for warning and error messages.
     */
    console.warn(_consoleMessage);
    table.processing(false);
    $('#dtprv_processing').css({'display': 'none'});
    $('#dtprv_wrapper').find('#dtprv_failure_message').remove();
    $('#dtprv_wrapper').find('.dt-scroll').before('<div id="dtprv_failure_message" class="alert alert-dismissible show alert-' + _type + '"><p>' + _message + '</p></div>');
  }

  function render_ajax_failure(_message){
    /**
     * Render the AJAX failures in console log and UI.
     */
    _render_failure(_message, ajaxErrorMessage, 'warning');
  }

  function render_timing_info(){
    /**
     * Render timing and estimated total info.
     *
     * Also save non HTML versions for use throughout functional code.
     *
     * NOTE: this is done separate from render_table_info
     *       due to how ajax complete callbacks and draw callbacks
     *       work in DataTables.
     */
    let countInfo = $('#dtprv_info');
    let info = '';
    if( typeof didEstimatedTotal != 'undefined' && didEstimatedTotal != null ){
      if( didEstimatedTotal ){
        info += estimatedLabel;
      }else{
        info += exactLabel;
      }
    }
    if( typeof ajaxElapsedTime != 'undefined' && ajaxElapsedTime != null ){
      if( info.length > 0 ){
        info += '\n';
      }
      info += (ajaxElapsedTime / 1000).toFixed(2) + ' ' + elapsedTimeLabel;
    }
    if( info.length == 0 ){
      $(countInfo).find('#timing-info').remove();
      return;
    }
    if( $(countInfo).find('#timing-info').length == 0 ){
      $(countInfo).append('&nbsp;<i class="fa fa-info-circle" id="timing-info"></i>');
    }
    $(countInfo).find('#timing-info').attr('title', info);
  }

  function render_table_info(){
    /**
     * Render table and resource info for the current table state.
     *
     * Also save non HTML versions for use throughout functional code.
     */
    // TODO: save table info into object...

    let resourceInfo = $('#dtv-resource-info');
    let content = $(resourceInfo).find('.dtv-resource-info-content');
    $(resourceInfo).find('i').attr('title', content.text());
    $(resourceInfo).show();

    let pagingWrapper = $('#dtprv_wrapper').find('.dt-paging');
    if( pagingWrapper.length > 0 ){
      $('#dtprv_wrapper').find('.dt-sorting-info').remove();
      let sortInfo = table.order();
      let sortingText = '<span class="info-label">' + colSortLabel + '&nbsp;</span>';
      if( sortInfo.length > 0 ){
        for( let i = 0; i < sortInfo.length; i++ ){
          let column = table.column(sortInfo[i][0]);
          let ds_type = $(column.header()).attr('data-ds-type');
          let dsID = $(column.header()).attr('data-name');
          let colLabel = dsID;
          if( colLabel != '_id' ){
            colLabel = _get_translated(keyedDataDictionary[dsID]['info'], 'label');
          }
          sortingText += '<span class="info-value"><em>' + colLabel + '&nbsp;';
          let downIcon = 'fas fa-sort-amount-down';
          let upIcon = 'fas fa-sort-amount-up';
          if( numberTypes.includes(ds_type) ){
            downIcon = 'fas fa-sort-numeric-down-alt';
            upIcon = 'fas fa-sort-numeric-up-alt';
          }else if( alphaTypes.includes(ds_type) ){
            downIcon = 'fas fa-sort-alpha-down-alt';
            upIcon = 'fas fa-sort-alpha-up-alt';
          }
          if( sortInfo[i][1] == 'asc' ){
            sortingText += '<sup><i title="' + colSortAscLabel + '" aria-label="' + colSortAscLabel + '" class="' + upIcon + '"></i></sup>';
          }else if( sortInfo[i][1] == 'desc' ){
            sortingText += '<sup><i title="' + colSortDescLabel + '" aria-label="' + colSortDescLabel + '" class="' + downIcon + '"></i></sup>';
          }else{
            sortingText += '<sup><i title="' + colSortAnyLabel + '" aria-label="' + colSortAnyLabel + '" class="fas fa-random"></i></sup>';
          }
          sortingText += '</em></span>';
        }
      }
      let sortDisplay = '<div class="dt-sorting-info">' + sortingText + '</div>';
      $(pagingWrapper).after(sortDisplay);
    }
  }

  function bind_column_filter(_column, _index){
    /**
     * Bind event handling for the column filters/search inputs.
     */
    if( ! _index >= colOffset ){
      return;  // _id col
    }

    function _bind_column_filter(_inputObj){
      if( _inputObj.length == 0 ){
        // TODO: unable to bind...fallback??
        return;
      }

      // set placeholder content
      let dsID = $(_column.header()).attr('data-name');
      let colLabel = _get_translated(keyedDataDictionary[dsID]['info'], 'label');
      $(_inputObj).attr('placeholder', colSearchLabel + ' ' + colLabel);

      let clearButton = $(_inputObj).parent().find('.dtcc-search-clear');
      $(clearButton).off('click.clearFilter');
      $(clearButton).on('click.clearFilter', function(_event){
        $(_inputObj).val('').focus().blur();
        _column.search(null).draw();
        $(clearButton).hide();
      });

      if( $(_inputObj).val().length > 0 ){
        // show button on initial paint if column search
        $(clearButton).show();
      }

      $(_inputObj).off('keyup.filterCol');
      $(_inputObj).on('keyup.filterCol', function(_event){
        let _fVal = $(_inputObj).val();
        if( _event.keyCode == 13 && _column.search() !== _fVal ){
          _column.search(_fVal).draw();
          if( _fVal.length > 0 ){
            $(clearButton).show();
          }else{
            $(clearButton).hide();
          }
        }
      });
    }

    let searchFilterInput = $(_column.footer()).find('input');
    if( searchFilterInput.length > 0 ){
      _bind_column_filter(searchFilterInput);
      return;
    }else{
      const maxTries = 35;
      let interval = false;
      let tries = 0;
      interval = setInterval(function(){
        searchFilterInput = $(_column.footer()).find('input');
        if( searchFilterInput.length > 0 || tries > maxTries ){
          clearInterval(interval);
          interval = false;
          _bind_column_filter(searchFilterInput);
        }
        tries++;
      }, 150);
    }
  }

  function bind_custom_events(){
    /**
     * Bind custom jQuery events.
     */
    $('#dtprv').dataTable().api().columns().every(function(_i){
      bind_column_filter(this, _i);
    });
  }

  function set_row_selects(){
    /**
     * Set selected rows based on table saved state.
     */
    // FIXME: row selects state...
    if( typeof tableState != 'undefined' && typeof tableState.selected != 'undefined' ){
      table.rows(tableState.selected).select();
    }
  }

  function set_button_states(){
    /**
     * Modify table buttons based on table interaction.
     */
    let buttons = $('#dtprv_wrapper').find('.dt-buttons').find('.btn.disabled');
    if( buttons.length > 0 ){
      $(buttons).each(function(_index, _button){
        $(_button).attr('disabled', true);
      });
    }

    let tableModified = false;

    $('.dt-buttons button.resetButton').removeClass('btn-secondary').removeClass('disabled').addClass('btn-warning');
    // TODO: reset button control
    // if( typeof tableState != 'undefined' && tableState != _data ){
    //   $('.dt-buttons button.resetButton').removeClass('btn-secondary').removeClass('disabled').addClass('btn-warning');
    // }else{
    //   $('.dt-buttons button.resetButton').removeClass('btn-warning').addClass('btn-secondary').addClass('disabled');
    // }
  }

  function set_table_visibility(){
    /**
     * Set various visibilities to help with table flashing
     * layout changes when DataTables initializes.
     */
    $('#dtprv').css({'visibility': 'visible'});
    $('#dtv-resource-info').css({'visibility': 'visible'});
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
    /**
     * Set various visibilities to help with table flashing
     * layout changes when we switch from Compact view to Table view.
     */
    $('#dtprv').css({'visibility': 'hidden'});
    $('#dtv-resource-info').css({'visibility': 'hidden'});
    $('.dt-scroll-head').css({'visibility': 'hidden'});
    $('.dt-scroll-head').find('th.expanders').css({'visibility': 'hidden'});
    $('.dt-length').css({'visibility': 'hidden'});
    $('.dt-search').css({'visibility': 'hidden'});
    $('#dtprv-editor-button').css({'visibility': 'hidden'});
    $('#dtprv-editor-button').find('button').css({'display': 'none'});
  }

  function draw_callback(_settings){
    /**
     * Executes whenever the DataTable draws.
     */
    $('#dtprv_wrapper').find('#dtprv_failure_message').remove();
    set_table_visibility();
    render_table_info();
    render_timing_info();
    set_button_states();
  }

  function init_callback(_setting, _data){
    /**
     * Executes once the DataTable initializes.
     */
    set_table_visibility();
    if( ! isCompactView ){
      table.columns.adjust();
    }
    ajaxElapsedTime = window.performance.now() - ajaxStartTime;  // track ajax performance time
    didEstimatedTotal = _data.total_was_estimated;
    render_timing_info();
    set_row_selects();
    bind_custom_events();
    set_button_states();
  }

  function state_save_callback(_settings, _data){
    /**
     * Executes whenever the DataTable tries to save the state.
     *
     * NOTE: we save it by the Resource View ID instead of the default
     *       page pathname so multiple DataTables work on the same page,
     *       and using the Fullscreen view respects the state saves.
     *
     * NOTE: we set the local tableState values here so we can access
     *       tableState easily throughout the functional code.
     */
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

    // custom local storage name for multiple table views and fullscreen views
    window.localStorage.setItem('DataTables_dtprv_' + viewID, JSON.stringify(_data));
  }

  function state_load_callback(_settings){
    /**
     * Executes whenever the DataTable tries to load the state.
     *
     * NOTE: we load it by the Resource View ID instead of the default
     *       page pathname so multiple DataTables work on the same page,
     *       and using the Fullscreen view respects the state saves.
     *
     * NOTE: we set the local tableState values here so we can access
     *       tableState easily throughout the functional code.
     */
    if( ! doStateSave ){
      return;
    }

    let _data = JSON.parse(window.localStorage.getItem('DataTables_dtprv_' + viewID));

    let localInstanceState = typeof tableState != 'undefined' ? tableState : _data;
    tableState = _data;

    tableState.page_number = localInstanceState.page_number;
    tableState.page_length = localInstanceState.page_length;
    tableState.selected = localInstanceState.selected;
    tableState.sort_order = localInstanceState.sort_order;
    tableState.compact_view = localInstanceState.compact_view;

    return _data;
  }

  function apply_ajax_ckan_filters(_data){
    /**
     * Modify the data sent via AJAX.
     */
    ajaxStartTime = window.performance.now();  // track ajax performance time

    if( ckanFilters != null ){
      _data.filters = ckanFilters;
    }
  }

  function ajax_complete_callback(_data){
    /**
     * Callback to the AJAX completion.
     */
    ajaxElapsedTime = window.performance.now() - ajaxStartTime;  // track ajax performance time

    if( _data.responseJSON ){
      if( ! _data.responseJSON.data ){
        render_ajax_failure('DataTables error - ' + _data.status + ': ' + _data.statusText);
        return;
      }
      didEstimatedTotal = _data.responseJSON.total_was_estimated;
    }else{
      render_ajax_failure('DataTables error - ' + _data.status + ': ' + _data.statusText);
    }
  }

  function initialize_datatable(){
    /**
     * Initializes the DataTable object.
     *
     * NOTE: this is done functionaly so we can destroy and
     *       re-initialize the table without page reloading.
    */
    table = $('#dtprv').DataTable({
      paging: true,
      serverSide: true,
      processing: true,
      responsive: isCompactView,
      autoWidth: true,
      stateSave: doStateSave,
      stateDuration: stateSaveDuration,
      // TODO: disallow moving the _id col
      colReorder: {
        fixedColumnsLeft: 1
      },
      columnControl: [
        {
          "target": "thead",
          "content": ["order"]
        },
        {
          "target": "tfoot",
          "content": ["search"]
        }
      ],
      ordering: {
        indicators: false,
        handler: false
      },
      // TODO: disallow moving the _id col
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
        "data": apply_ajax_ckan_filters,
        "headers": {
          'X-CSRF-Token': $('meta[name="' + csrfTokenName + '"]').attr('content'),
        },
        "complete": ajax_complete_callback,
      },
      initComplete: init_callback,
      drawCallback: draw_callback,
      stateSaveCallback: state_save_callback,
      stateLoadCallback: state_load_callback,
      buttons: get_available_buttons(),
    });
  }

  initialize_datatable();
}
