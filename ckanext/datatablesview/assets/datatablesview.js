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
      showSummaryRow: false,
      showHistograms: false,
      pageLengthChoices: [20, 50, 100, 500, 1000],
      resourceUrl: null,
      dataDictionary: null,
      editable: false,
      timeout: 60000,
    },
    initialize: function(){
      /**
       * Call functional code so we can destory and re-initialize the DataTable objects
       * we need to, instead of the entire CKAN module object (or requiring page reload).
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

function _linkify(_data){
  const linksFound = _data.match(/(\b(https?)[-A-Z0-9+&@#\/%?=~_|!:,.;]*[-A-Z0-9+&@#\/%=~_|])/ig);
  let links = [];
  let output;
  if( linksFound != null ){
    if( linksFound.length === 1 && _data.match(/\.(jpeg|jpg|gif|png|svg|apng|webp|avif)$/i) ){
      // the whole text is just one link and its a picture, create a thumbnail
      output = '<div class="dt-thumbnail"><a href="' + linksFound[0] + '" target="_blank"><img alt="" src="' + linksFound[0] + '"></a></div>';
      return {text: output, links: linksFound};
    }
    for( let i = 0; i < linksFound.length; i++ ){
      links.push('<a href="' + linksFound[i] + '" target="_blank">' + linksFound[i] + '</a>');
      output = _data.split(linksFound[i]).map(function(item){return item}).join(links[i]);
    }
    return {text: output, links: linksFound};
  }
  return {text: _data, links: []};
}

function load_datatable(CKAN_MODULE){
  const _ = CKAN_MODULE._;
  const hasEllipsisExpandFeat = false;  // TODO: make JS expand/hide remaining content for ellipses...

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
  const showSummaryRow = CKAN_MODULE.options.showSummaryRow;
  const showHistograms = CKAN_MODULE.options.showHistograms;
  const pageLengthChoices = CKAN_MODULE.options.pageLengthChoices;
  const resourceURI = CKAN_MODULE.options.resourceUrl;
  const dataDictionary = CKAN_MODULE.options.dataDictionary;
  const isEditable = CKAN_MODULE.options.editable;
  const requestTimeout = CKAN_MODULE.options.timeout;
  const csrfTokenName = $('meta[name="csrf_field_name"]').attr('content');

  const TABLE_LANGUAGE = {
    errors: {
      ajax: _('Error: Could not query records. Please try again.'),
    },
    buttons: {
      full: _('Full Table'),
      compact: _('Compact Table'),
      copy: _('Copy to clipboard'),
      colvis: {
        toggle: _('Toggle column visibility'),
        restore: _('Restore visibility'),
        all: _('Show all'),
        none: _('Show none'),
        filtered: _('Filtered'),
      },
      download: _('Filtered download'),
      reset: _('Reset'),
      print: _('Print'),
      share: _('Share current view'),
    },
    renderers: {
      less: _('less'),
    },
    info: {
      column: {
        search: _('Search:'),
        sort: _('Sorting by:'),
        asc: _('Ascending'),
        desc: _('Descending'),
        any: _('Any'),
      },
      result: {
        estimated: _('Total was estimated'),
        exact: _('Total is exact'),
        elapsed: _('seconds'),
      },
      summary: {
        total: _('Total:'),
        average: _('Average:'),
        range: _('Range:'),
        dateRange: _('Date Range:'),
      }
    },
    print: {
      dataUpdated: _('Data last updated:'),
      metadataUpdated: _('Metadata last updated:'),
      created: _('Created:'),
      format: _('Format:'),
      fileSize: _('File size:'),
      dataDictionary: _('Data Dictionary'),
      id: _('ID'),
      type: _('Type'),
      label: _('Label'),
      description: _('Description'),
    }
  }

  const CELL_DISPLAY_RENDERERS = {
    'text': function(_data, _type, _row, _meta, _dictionary_field){
      /**
       * Our custom Cell renderer for text type cells in the table.
       */
      return DataTable.render.ellipsis(ellipsisLength, _meta.row, _dictionary_field.id)(_data, _type, _row, _meta);
    },
    'text_array': function(_data, _type, _row, _meta, _dictionary_field){
      /**
       * Our custom Cell renderer for text array type cells in the table.
       */
      if( ! Array.isArray(_data) ){
        _data = _data.toString().split(',');  // split to Array if not already
      }
      let displayList = '<ul class="text-left">';
      _data.forEach(function(_val, _i, _arr){
        displayList += '<li>' + _val + '</li>';
      });
      displayList += '</ul>';
      return displayList;
    },
    'bool': function(_data, _type, _row, _meta, _dictionary_field){
      /**
       * Our custom Cell renderer for boolean type cells in the table.
       */
      return 'TRUE' ? _data === true : 'FALSE';
    },
    'number': function(_data, _type, _row, _meta, _dictionary_field){
      /**
       * Our custom Cell renderer for number type cells in the table.
       */
      // TODO: add number format configs/options ??
      // number(THOUSAND, DECIMAL, PRECISION, PREFIX, POSTFIX)
      return DataTable.render.number(null, null, 2, null, null).display(_data, _type, _row);
    },
    'date': function(_data, _type, _row, _meta, _dictionary_field){
      /**
       * Our custom Cell renderer for datetime type cells in the table.
       */
      if( ! _data.toString().includes('+0000') ){
        _data = _data.toString() + '+0000';  // add UTC offset if not present
      }
      return DataTable.render.moment(window.moment.ISO_8601, dateFormat, languageCode)(_data, _type, _row, _meta);
    },
  };

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
    'money',
  ];
  const alphaTypes = [
    'text',
    '_text',
  ];
  const dateTypes = [
    'timestamp',
    'date',
  ]
  const colOffset = 1;  // _id col
  const defaultSortOrder = [[0, "asc"]];  // _id col
  const defaultPageNumber = 0;
  const defaultSelectedRows = [];
  let ajaxStartTime = 0;
  let ajaxElapsedTime;
  let sortDisplay;
  let countDisplay;
  let sortDisplayCopy;
  let countDisplayCopy;

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
  let startPageNumber = typeof tableState != 'undefined' && typeof tableState.page_number != 'undefined' ? tableState.page_number : defaultPageNumber;
  let selectedRows = typeof tableState != 'undefined' && typeof tableState.selected != 'undefined' ? tableState.selected : defaultSelectedRows;
  let didEstimatedTotal;

  let availableColumns = [{
    "targets": 0,
    "name": '_id',
    "data": '_id',
    "searchable": false,
    "colReorder": false,
    "type": 'num',
    "className": 'dt-body-right datatable-id-col',
    "width": isCompactView ? '28px' : '50px',
  }];
  const defaultColOrder = [0];

  for( let i = 0; i < dataDictionary.length; i++ ){
    /**
     * Available data types for DataTables JS found here:
     * https://datatables.net/reference/option/columns.type
     *
     * TODO: make this pluggable with CKAN_MODULE.options
     *       somehow to allow for extensions that use more
     *       specific DataStore types???
     */
    let _colType = 'string';
    if( numberTypes.includes(dataDictionary[i].type) ){
      _colType = 'num';
    }else if( dateTypes.includes(dataDictionary[i].type) ){
      _colType = 'date';
    }
    let _cellRenderer = CELL_DISPLAY_RENDERERS.text;
    if( dataDictionary[i].type == '_text' ){
      _cellRenderer = CELL_DISPLAY_RENDERERS.text_array;
    }else if( numberTypes.includes(dataDictionary[i].type) ){
      _cellRenderer = CELL_DISPLAY_RENDERERS.number;
    }else if( dateTypes.includes(dataDictionary[i].type) ){
      _cellRenderer = CELL_DISPLAY_RENDERERS.date;
    }
    // TODO: add money formatting ??
    availableColumns.push({
      "name": dataDictionary[i].id,
      "data": dataDictionary[i].id,
      "searchable": true,
      "type": _colType,
      "render": function(_data, _type, _row, _meta){
        if( _type != 'display' ){
          return _data;
        }
        if( _data == null ){
          // TODO: make configurable??
          return '';  // blank cell for None/null values
        }
        if( _data === true || _data === false ){
          // special case for boolean types
          return CELL_DISPLAY_RENDERERS.bool(_data, _type, _row, _meta, dataDictionary[i]);
        }
        return _cellRenderer(_data, _type, _row, _meta, dataDictionary[i]);
      }
    });
    defaultColOrder.push(i + 1);
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
     *
     * Links will be rendered into possible image thumbnails
     * and HTML achor tags. Ellipsis text will split before any anchor elements.
     */
    return function(_data, _type, _row, _meta){
      if( _type == 'display' ){
        let str = _data.toString();
        let linkifiedData = _linkify(str);
        let strippedData = linkifiedData.text.replace(/(<([^>]+)>)/gi, '');
        if( strippedData.length <= _cutoff ){
          return linkifiedData.text;
        }
        let preview;
        let remaining;
        if( linkifiedData.links.length > 0 ){
          // cutoff before anchor element
          let linkpos = _cutoff;
          let lastpos = _cutoff;
          let lastlink = '';
          let addLen = 0;
          // check if truncation point is in the middle of a link
          for( const aLink of linkifiedData.links ){
            linkpos = str.indexOf(aLink);
            if( linkpos + aLink.length >= _cutoff ){
              // truncation point is in the middle of a link, truncate to where the link started
              break
            }else{
              addLen = addLen + lastlink.length ? (lastlink.length) + 31 : 0;  // 31 is the number of other chars in the full anchor tag
              lastpos = linkpos;
              lastlink = aLink;
            }
          }
          preview = linkifiedData.text.substr(0, lastpos + addLen).trimEnd();
          if( hasEllipsisExpandFeat ){  // TODO: make JS expand/hide remaining content for ellipses...
            remaining = linkifiedData.text.substr(lastpos + addLen).trimEnd();
          }
        }else{
          preview = str.substr(0, _cutoff - 1);
          if( hasEllipsisExpandFeat ){  // TODO: make JS expand/hide remaining content for ellipses...
            remaining = str.substr(_cutoff - 1);
          }
        }
        let _elementID = 'datatableReadMore_' + _rowIndex + '_' + _datatoreID;
        let expander = '<span>&#8230;</span>';
        if( hasEllipsisExpandFeat ){  // TODO: make JS expand/hide remaining content for ellipses...
          expander = '<a class="datatable-readmore-expander" href="javascript:void(0);" data-toggle="collapse" data-bs-toggle="collapse" aria-expanded="false" aria-controls="' + _elementID + '">&#8230;</a>';
        }
        preview += expander;
        // TODO: make JS expand/hide remaining content for ellipses...
        return hasEllipsisExpandFeat ? '<div class="datatable-readmore"><span>' + preview + '</span><span class="collapse" id="' + _elementID + '">' + remaining + '<a class="datatable-readmore-minimizer" href="javascript:void(0);" data-toggle="collapse" data-bs-toggle="collapse" aria-expanded="true" aria-controls="' + _elementID + '"><small>[' + TABLE_LANGUAGE.renderers.less + ']</small></a><span></div>' : '<div class="datatable-readmore"><span>' + preview + '</span></div>';
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
    if( typeof _obj == 'undefined' || typeof _obj[_key] == 'undefined' ){
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

  function _get_visible_col_ids(){
    /**
     * Return array of field IDs that have their columns visible
     */
    let visibleColIndices = table.columns(':visible').indexes().toArray();
    let visibleIDs = [];
    for( _i = 0; _i <= visibleColIndices.length; _i++ ){
      let column = table.column(visibleColIndices[_i]);
      if( $(column.header()).attr('data-name') == '_id' ){
        continue;
      }
      visibleIDs.push($(column.header()).attr('data-name'));
    }
    return visibleIDs;
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
        titleAttr: isCompactView ? TABLE_LANGUAGE.buttons.full : TABLE_LANGUAGE.buttons.compact,
        className: 'btn-secondary',
        action: function(e, dt, node, config){
          if( isCompactView ){
            dt.button('viewToggleButton:name').text('<i class="fa fa-table"></i>');
            isCompactView = false;
          } else {
            dt.button('viewToggleButton:name').text('<i class="fa fa-list"></i>');
            isCompactView = true;
          }
          // special case for selected rows when switching between Full/Compact tables
          tableState.selected = table.rows({ selected: true })[0];
          dt.state.save();
          set_state_change_visibility();
          dt.clear().destroy();
          initialize_datatable();
        }
      },
      {
        extend: 'copy',
        text: '<i class="fa fa-copy"></i>',
        titleAttr: TABLE_LANGUAGE.buttons.copy,
        className: 'btn-secondary',
        messageTop: function(){
          /**
           * Add all of the table filter info to the clipboard
           */
          // FIXME: should this info just be in messageBottom??
          //        people might just want th data rigth at the top?
          let copyInfo = packageName + ' — ' + resourceName + '\n' + resourceURI + '\n';
          copyInfo += countDisplayCopy + '\n' + sortDisplayCopy + '\n'
          copyInfo += TABLE_LANGUAGE.print.dataUpdated + ' ' + dataUpdatedDate + '\n'
          copyInfo += TABLE_LANGUAGE.print.metadataUpdated + ' ' + metadataUpdatedDate + '\n';
          copyInfo += TABLE_LANGUAGE.print.created + ' ' + createdDate + '\n';
          copyInfo += TABLE_LANGUAGE.print.format + ' ' + resourceFormat + '\n';
          let filesize = resourceFileSizeHumanized ? resourceFileSizeHumanized : resourceFileSize + ' bytes';
          copyInfo += TABLE_LANGUAGE.print.fileSize + ' ' + filesize + '\n';
          return copyInfo;
        },
        messageBottom: function(){
          /**
           * Add a simple Data Dictionary output to the clipboard
           *
           * Only output info for the visible columns
           */
          let visibleColNames = _get_visible_col_ids();
          let copyDictionary = TABLE_LANGUAGE.print.dataDictionary;
          let copyIndex = 1;
          for( let _i = 0; _i < dataDictionary.length; _i++ ){
            if( ! visibleColNames.includes(dataDictionary[_i]['id']) ){
              continue;
            }
            let colLabel = _get_translated(dataDictionary[_i]['info'], 'label');
            if( colLabel == null ){
              colLabel = dataDictionary[_i]['id'];
            }
            copyDictionary += '\n\n' + (copyIndex) + '. ' + colLabel;
            if( colLabel != dataDictionary[_i]['id'] ){
              copyDictionary += '\n' + TABLE_LANGUAGE.print.id + '   ' + dataDictionary[_i]['id'];
            }
            copyDictionary += '\n' + TABLE_LANGUAGE.print.type + '   ' + dataDictionary[_i]['type'];
            let colNotes = _get_translated(dataDictionary[_i]['info'], 'notes');
            if( colNotes != null ){
              copyDictionary += '\n' + TABLE_LANGUAGE.print.description + '   ' + colNotes;
            }
            copyIndex++;
          }
          return copyDictionary;
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
        titleAttr: TABLE_LANGUAGE.buttons.colvis.toggle,
        className: 'btn-secondary',
        columns: 'th:gt(0)',
        collectionLayout: 'fixed dt-popup-colvis',
        postfixButtons: [
          {
            extend: 'colvisRestore',
            text: '<i class="fa fa-undo"></i> ' + TABLE_LANGUAGE.buttons.colvis.restore,
          },
          {
            extend: 'colvisGroup',
            text: '<i class="fa fa-eye"></i> ' + TABLE_LANGUAGE.buttons.colvis.all,
            show: ':hidden'
          },
          {
            extend: 'colvisGroup',
            text: '<i class="fa fa-eye-slash"></i> ' + TABLE_LANGUAGE.buttons.colvis.none,
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
            text: '<i class="fa fa-filter"></i> ' + TABLE_LANGUAGE.buttons.colvis.filtered,
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
        titleAttr: TABLE_LANGUAGE.buttons.download,
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
        titleAttr: TABLE_LANGUAGE.buttons.reset,
        className: 'btn-secondary disabled resetButton',
        action: function (e, dt, node, config) {
          set_state_change_visibility();
          if( $('.dt-buttons button.resetButton').hasClass('btn-warning') ){
            $('.dt-buttons button.resetButton').removeClass('btn-warning').addClass('btn-secondary');
          }
          if( ! defaultCompactView ){
            dt.button('viewToggleButton:name').text('<i class="fa fa-table"></i>');
            isCompactView = false;
          } else {
            dt.button('viewToggleButton:name').text('<i class="fa fa-list"></i>');
            isCompactView = true;
          }
          dt.rows().deselect();  // special case for selected rows
          dt.colReorder.reset(); // reset the column ordering
          tableState = void 0;  // clear local state variable
          dt.state.clear();
          dt.clear().destroy();
          initialize_datatable();
        }
      },
      {
        extend: 'print',
        text: '<i class="fa fa-print"></i>',
        titleAttr: TABLE_LANGUAGE.buttons.print,
        className: 'btn-secondary',
        title: packageName + ' — ' + resourceName,
        messageTop: function(){
          /**
           * Add all of the table filter info to the print head
           */
          // FIXME: should this info just be in messageBottom??
          //        people might just want th data rigth at the top?
          let printInfo = '<div>';
          printInfo += countDisplay + sortDisplay;
          printInfo += '<span><a href="' + resourceURI + '">' + packageName + ' — ' + resourceName + '</a></span><br/>';
          printInfo += '<span>' + TABLE_LANGUAGE.print.dataUpdated + ' ' + dataUpdatedDate + '</span><br/>';
          printInfo += '<span>' + TABLE_LANGUAGE.print.metadataUpdated + ' ' + metadataUpdatedDate + '</span><br/>';
          printInfo += '<span>' + TABLE_LANGUAGE.print.created + ' ' + createdDate + '</span><br/>';
          printInfo += '<span>' + TABLE_LANGUAGE.print.format + ' ' + resourceFormat + '</span><br/>';
          let filesize = resourceFileSizeHumanized ? resourceFileSizeHumanized : resourceFileSize + ' bytes';
          printInfo += '<span>' + TABLE_LANGUAGE.print.fileSize + ' ' + filesize + '</span><br/>';
          printInfo += '</div>';
          return printInfo;
        },
        messageBottom: function(){
          /**
           * Add a simple Data Dictionary output to the print footer
           *
           * Only output info for the visible columns
           */
          let visibleColNames = _get_visible_col_ids();
          let printDictionary = '<div><h2>' + TABLE_LANGUAGE.print.dataDictionary + '</h2><ol>';
          for( let _i = 0; _i < dataDictionary.length; _i++ ){
            if( ! visibleColNames.includes(dataDictionary[_i]['id']) ){
              continue;
            }
            let colLabel = _get_translated(dataDictionary[_i]['info'], 'label');
            if( colLabel == null ){
              colLabel = dataDictionary[_i]['id'];
            }
            printDictionary += '<li><span>' + colLabel + '</span>';
            if( colLabel != dataDictionary[_i]['id'] ){
              printDictionary += '<br/><strong>' + TABLE_LANGUAGE.print.id + '</strong>&nbsp;&nbsp;&nbsp;<span>' + dataDictionary[_i]['id'] + '</span>';
            }
            printDictionary += '<br/><strong>' + TABLE_LANGUAGE.print.type + '</strong>&nbsp;&nbsp;&nbsp;<span>' + dataDictionary[_i]['type'] + '</span>';
            let colNotes = _get_translated(dataDictionary[_i]['info'], 'notes');
            if( colNotes != null ){
              printDictionary += '<br/><strong>' + TABLE_LANGUAGE.print.description + '</strong>&nbsp;&nbsp;&nbsp;<span>' + colNotes + '</span>';
            }
            printDictionary += '</li>';
          }
          printDictionary += '</ol></div>';
          return printDictionary;
        },
        exportOptions: {
          columns: ':visible',
          stripHtml: false,
          format: {
            // workaround for <br> being filtered out in DataTables during printing
            body: function (_d, _r, _c, _n){
              let clone = _n.cloneNode(true);
              clone.querySelectorAll('br').forEach(function(_e){
                _e.replaceWith('\n');
              });
              return clone.innerHTML;
            }
          }
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
      //   titleAttr: TABLE_LANGUAGE.buttons.share,
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
    _render_failure(_message, TABLE_LANGUAGE.errors.ajax, 'warning');
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
        info += TABLE_LANGUAGE.info.result.estimated;
      }else{
        info += TABLE_LANGUAGE.info.result.exact;
      }
    }
    if( typeof ajaxElapsedTime != 'undefined' && ajaxElapsedTime != null ){
      if( info.length > 0 ){
        info += '\n';
      }
      info += (ajaxElapsedTime / 1000).toFixed(2) + ' ' + TABLE_LANGUAGE.info.result.elapsed;
    }
    if( info.length == 0 ){
      $(countInfo).find('#timing-info').remove();
      return;
    }
    if( $(countInfo).find('#timing-info').length == 0 ){
      $(countInfo).append('&nbsp;<i class="fa fa-info-circle dt-display-screen" id="timing-info"></i><span class="dt-display-print" id="timing-info-print"></span>');
    }
    $(countInfo).find('#timing-info').attr('title', info);
    $(countInfo).find('#timing-info-print').html('<br/>' + info.replace('\n', '<br/>'));
    countDisplay = $(countInfo).html();
    let countInfoText = $(countInfo).clone();
    $(countInfoText).find('#timing-info').remove();
    $(countInfoText).find('#timing-info-print').remove();
    countInfoText = $(countInfoText).text();
    countInfoText += '\n' + info;
    countDisplayCopy = countInfoText;
  }

  function render_table_info(){
    /**
     * Render table and resource info for the current table state.
     *
     * Also save non HTML versions for use throughout functional code.
     */
    let resourceInfo = $('#dtv-resource-info');
    let content = $(resourceInfo).find('.dtv-resource-info-content');
    $(resourceInfo).find('i').attr('title', content.text());
    $(resourceInfo).show();

    let pagingWrapper = $('#dtprv_wrapper').find('.dt-paging');
    if( pagingWrapper.length > 0 ){
      $('#dtprv_wrapper').find('.dt-sorting-info').remove();
      let sortInfo = table.order();
      let sortingText = '<span class="info-label">' + TABLE_LANGUAGE.info.column.sort + '&nbsp;</span>';
      let sortingTextCopy = TABLE_LANGUAGE.info.column.sort + ' ';
      if( sortInfo.length > 0 ){
        for( let i = 0; i < sortInfo.length; i++ ){
          let column = table.column(sortInfo[i][0]);
          let ds_type = $(column.header()).attr('data-ds-type');
          let dsID = $(column.header()).attr('data-name');
          let colLabel = dsID;
          if( colLabel != '_id' ){
            colLabel = _get_translated(keyedDataDictionary[dsID]['info'], 'label');
            if( colLabel == null ){
              colLabel = dsID;
            }
          }
          sortingText += '<span class="info-value"><em>' + colLabel + '&nbsp;';
          sortingTextCopy += colLabel + ' ';
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
            sortingText += '<span class="dt-display-print">(' + TABLE_LANGUAGE.info.column.asc + ')</span><sup><i title="' + TABLE_LANGUAGE.info.column.asc + '" aria-label="' + TABLE_LANGUAGE.info.column.asc + '" class="dt-display-screen ' + upIcon + '"></i></sup>';
            sortingTextCopy += '(' + TABLE_LANGUAGE.info.column.asc + ')';
          }else if( sortInfo[i][1] == 'desc' ){
            sortingText += '<span class="dt-display-print">(' + TABLE_LANGUAGE.info.column.desc + ')</span><sup><i title="' + TABLE_LANGUAGE.info.column.desc + '" aria-label="' + TABLE_LANGUAGE.info.column.desc + '" class="dt-display-screen ' + downIcon + '"></i></sup>';
            sortingTextCopy += '(' + TABLE_LANGUAGE.info.column.desc + ')';
          }else{
            sortingText += '<span class="dt-display-print">(' + TABLE_LANGUAGE.info.column.any + ')</span><sup><i title="' + TABLE_LANGUAGE.info.column.any + '" aria-label="' + TABLE_LANGUAGE.info.column.any + '" class="dt-display-screen fas fa-random"></i></sup>';
            sortingTextCopy += '(' + TABLE_LANGUAGE.info.column.any + ')';
          }
          sortingText += '</em></span>';
        }
      }
      sortDisplay = '<div class="dt-sorting-info">' + sortingText + '</div>';
      sortDisplayCopy = sortingTextCopy;
      $(pagingWrapper).after(sortDisplay);
    }
  }

  function render_summary_stats(){
    /**
     * Render the column summaries in their respective footer cell
     */
    // TODO: implement summary statistics when backend is ready
    // TODO: mean(average), median(middle), mode(frequent),
    //       spread(range), standard deviation, interquartile range 25% 75%,
    //       (range-min is 0% median is 50% range-max is 100% of IQR)
    // TODO: make summary row collapsable
    return;
    table.columns().every(function(){
      if( this.index() ){  // don't display for _id col
        if( this.visible() ){  // don't stat hidden cols
          let ds_type = $(this.header()).attr('data-ds-type');
          let dsID = $(this.header()).attr('data-name');
          let statCell = $('#dtprv_wrapper').find('tr#dt-summary-row').find('td[data-name="' + dsID + '"]');
          if( numberTypes.includes(ds_type) ){

          }else if( dateTypes.includes(ds_type) ){

          }
        }
      }
    });
  }

  function render_histograms(){
    /**
     * Render the histograms in their respective header cell
     */
    // TODO: implement histograms when backend is ready
    return;
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
      if( colLabel == null ){
        colLabel = dsID;
      }
      $(_inputObj).attr('placeholder', TABLE_LANGUAGE.info.column.search + ' ' + colLabel);

      let clearButton = $(_inputObj).parent().find('.dtcc-search-clear');
      $(clearButton).off('click.clearFilter');  // prevent duplicate events
      $(clearButton).on('click.clearFilter', function(_event){
        $(_inputObj).val('').focus().blur();
        _column.search(null).draw();
        $(clearButton).hide();
      });

      if( $(_inputObj).val().length > 0 ){
        // show button on initial paint if column search
        $(clearButton).show();
      }

      $(_inputObj).off('keyup.filterCol');  // prevent duplicate events
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

    // prevent selecting rows if clicking a link or image inside a cell
    table.off('user-select.preventLinkSelects');  // prevent duplicate events
    table.on('user-select.preventLinkSelects', function(_event, _dt, _type, _cell, _originalEvent) {
      if( $(_originalEvent.target).is('a') || $(_originalEvent.target).is('img') ){
        _event.preventDefault();
      }
    });

    // deselect rows during certain events
    table.off('page.deselectRows search.deselectRows order.deselectRows length.deselectRows');  // prevent duplicate events
    table.on('page.deselectRows search.deselectRows order.deselectRows length.deselectRows', function(e, dt, type){
      table.rows().deselect();
    });

    // set button states when selecting/deselecting rows
    table.off('select.setButtonStates deselect.setButtonStates');  // prevent duplicate events
    table.on('select.setButtonStates deselect.setButtonStates', function(e, dt, type, indexes){
      // special case for selected rows when switching between Full/Compact tables
      tableState.selected = table.rows({ selected: true })[0];
      set_button_states();
    });

    // set button states when changing column visibility and ordering
    table.off('column-visibility.setButtonStates columns-reordered.setButtonStates');  // prevent duplicate events
    table.on('column-visibility.setButtonStates columns-reordered.setButtonStates', function(e, dt, type){
      set_button_states();
    });
  }

  function set_row_selects(){
    /**
     * Set selected rows based on table saved state.
     */
    if( typeof selectedRows == 'undefined' ){
      return;
    }

    table.rows(selectedRows).select();
  }

  function set_button_states(){
    /**
     * Modify table buttons based on table interaction.
     */
    // BootStrap disabled buttons to DataTables disabled buttons
    let buttons = $('#dtprv_wrapper').find('.dt-buttons').find('.btn.disabled');
    if( buttons.length > 0 ){
      $(buttons).each(function(_index, _button){
        $(_button).attr('disabled', true);
      });
    }

    if( typeof tableState == 'undefined' || tableState == null ){
      return;  // nothing changed
    }

    function _set_button_states(_tableModified){
      if( ! _tableModified ){
        $('.dt-buttons button.resetButton').addClass('btn-secondary').addClass('disabled').removeClass('btn-warning').attr('disabled', true);
        return;  // state is same as default state
      }

      $('.dt-buttons button.resetButton').removeClass('btn-secondary').removeClass('disabled').addClass('btn-warning').attr('disabled', false);
    }

    if( tableState.page_number != 0 ){
      _set_button_states(true);  // page number has changed
      return;
    }
    if( tableState.page_length != pageLengthChoices[0] ){
      _set_button_states(true);  // page length has changed from configured
      return;
    }
    if( tableState.selected.length > 0 ){
      _set_button_states(true);  // rows have been selected
      return;
    }
    if( JSON.stringify(tableState.sort_order) !== JSON.stringify(defaultSortOrder) ){
      _set_button_states(true);  // sort order changed from configured
      return;
    }
    if( tableState.compact_view != defaultCompactView ){
      _set_button_states(true);  // table view type has changed from configured
      return;
    }
    if( table.columns(':hidden').indexes().toArray().length > 0 ){
      _set_button_states(true);  // column visibility has changed
      return;
    }
    if( JSON.stringify(tableState.column_order) !== JSON.stringify(defaultColOrder) ){
      _set_button_states(true);  // column ordering has changed
      return;
    }
    if( table.search().length > 0 ){
      _set_button_states(true);  // there is a table search
      return;
    }
    if( table.columns().search().toArray().some(function(_s){ return _s.length > 0; }) ){
      _set_button_states(true);  // there is a column search
      return;
    }

    _set_button_states(false);  // state is same as default state
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
    if( showSummaryRow ){
      // TODO: implement summary statistics when backend is ready
      render_summary_stats();
    }
    if( showHistograms ){
      // TODO: implement histograms when backend is ready
      render_histograms();
    }
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
    _data.column_order = this.api().colReorder.order();

    // special case for selected rows when switching between Full/Compact tables
    let localInstanceSelected = typeof tableState != 'undefined' ? tableState.selected : _data.selected;

    // update local JS table state object for easier code access
    tableState = Object.assign({}, tableState, _data);
    tableState.selected = localInstanceSelected;
    selectedRows = tableState.selected;

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

    if( _data == null ){
      return null;  // no saved state
    }

    // special case for selected rows when switching between Full/Compact tables
    let localInstanceSelected = typeof tableState != 'undefined' ? tableState.selected : _data.selected;

    // update local JS table state object for easier code access
    tableState = Object.assign({}, tableState, _data);
    tableState.selected = localInstanceSelected;
    selectedRows = tableState.selected;

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
      colReorder: {
        fixedColumnsLeft: 1,
        columns: ':not(:first-child)'
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
      fixedColumns: isCompactView ? false : {leftColumns: 1},
      orderCellsTop: true,
      mark: true,
      select: {
        style: 'os',
        blurable: true,
        selector: 'td:not(.dt-cell-histogram)' + (isCompactView ? ':not(.datatable-id-col)' : '')
      },
      scrollX: ! isCompactView,
      scrollY: 400,
      scrollResize: true,
      scrollCollapse: false,
      deferRender: true,
      pageLength: pageLength,
      displayStart: startPageNumber * pageLength,
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
