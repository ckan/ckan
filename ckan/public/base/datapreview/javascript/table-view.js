(function ($) {
  var dp = {};

  // Set up in DOM ready.
  dp.$dialog = null;

  // Time to wait for a JSONP request to timeout.
  dp.timeout = 5000;

  // Template url. The html property is populated from data-preview-templates.js
  dp.template = {
    html: ''
  };

  // Public: Sets up the dialog for displaying a full screen of data.
  //
  // dialogTitle - title for dialog window.
  //
  // Returns nothing.
  //
  dp.setupFullscreenDialog = function (dialogTitle) {
    var dialog = dp.$dialog;
    dialog.empty();
  }

  // Public: Displays a smaller alert style dialog with an error message.
  //
  // error - An error object to display.
  //
  // Returns nothing.
  //
  dp.showError = function (error) {
    var _html = '<p class="error">' + $.trim(error.title) + '</strong><br />' + $.trim(error.message) + '</p>';
    dp.$dialog.html(_html);
  };

  // Public: Displays the datapreview UI in a fullscreen dialog.
  //
  // This method also parses the data returned by the webstore for use in
  // the data preview UI.
  //
  // data    - An object of parsed CSV data returned by the webstore.
  //
  // Returns nothing.
  //
  dp.showData = function(data) {
    dp.setupFullscreenDialog();

    if(data.error) {
      return dp.showError(data.error);
    }
    var tabular = dp.convertData(data);

    // dp.loadTableView(tabular.columns, tabular.data);
    var columns = tabular.columns;
    var data = tabular.data;

    var element  = $(dp.template.html).appendTo(dp.$dialog);
    // set plot height explicitly or flot is not happy
    // also for grid
    var height = $(window).height();
    // $('.dataexplorer-tableview-viewer').height(height);
    $('.dataexplorer-tableview-grid').height(height);
    $('.dataexplorer-tableview-graph').height(height);
    var viewer   = new dp.createTableView(element, columns, data);

    // Load chart data from external source
    // TODO: reinstate
    // this used to load chart info from related CKAN dataset
    viewer.editor.loading();
    viewer.editor.loading(false).disableSave();

    // Save chart data to the client provided callback
    // TODO: implement
    viewer.editor.bind('save', function (chart) {
      viewer.editor.saving();
      viewer.editor.saving(false);
    });
  };

  // **Public: parse data from webstore or other source into form for data
  // preview UI**
  //
  // :param data: An object of parsed CSV data returned by the webstore.
  //
  // :return: parsed data.
  dp.convertData = function(data) {
    var tabular = {
      columns: [],
      data: []
    };
    isNumericRegex = (/^[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?$/);

    // two types of data: that from webstore and that from jsonpdataproxy
    // if fields then from dataproxy
    if (data.fields) {
      tabular.columns = $.map(data.fields || [], function (column, i) {
        return {id: 'header-' + i, name: column, field: 'column-' + i, sortable: true};
      });

      tabular.data = $.map(data.data || [], function (row, id) {
        var cells = {id: id};
        for (var i = 0, c = row.length; i < c; i++) {
          var isNumeric = isNumericRegex.test(row[i]);
          cells['column-' + i] = isNumeric ? parseFloat(row[i]) : row[i];
        }
        return cells;
      });
    } else {
      tabular.columns = $.map(data.keys, function(key, idx) {
        return {id: 'header-' + key, name: key, field: 'column-' + key, sortable: true};
      });
      tabular.data = $.map(data.data, function(row, id) {
        var cells = {id: id};
        for(i in row) {
          var val = row[i];
          var isNumeric = isNumericRegex.test(val);
          cells['column-' + tabular.columns[i].name] = isNumeric ? parseFloat(val) : val;
        }
        return cells;
      });
    }
    return tabular;
  };

  // Public: Kickstarts the plugin.
  //
  // dialogId    - The id of the dialog Element in the page.
  // options     - An object containing aditional options.
  //               timeout: Time in seconds to wait for a JSONP timeout.
  //
  // Returns nothing.
  //
  dp.initialize = function(dialogId, options) {
    dp.$dialog = $('#' + dialogId);
    options = options || {};

    dp.timeout = options.timeout || dp.timeout;

    var _height = Math.round($(window).height() * 0.6);

    // Large stylable dialog for displaying data.
    dp.dialogOptions = {
      autoOpen: false,
      // does not seem to work for width ...
      position: ['center', 'center'],
      buttons: [],
      width:  $(window).width()  - 20,
      height: $(window).height() - 20,
      resize: 'auto',
      modal: false,
      draggable: true,
      resizable: true
    };

    // Smaller alert style dialog for error messages.
    dp.errorDialogOptions = {
      title: 'Unable to Preview - Had an error from dataproxy',
      position: ['center', 'center'],
      buttons: [{
        text: "OK",
        click: function () { $(this).dialog("close"); }
      }],
      width: 360,
      height: 180,
      resizable: false,
      draggable: false,
      modal: true,
      position: 'fixed'
    };
  };

  // Export the DATAEXPLORER object onto the window.
  $.extend(true, window, {DATAEXPLORER: {}});
  DATAEXPLORER.TABLEVIEW = dp;

})(jQuery);
