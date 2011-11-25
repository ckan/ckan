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

  // **Public: Loads the plugin UI into the dialog and sets up event listeners.**
  //
  // columns - Column Array formatted for use in SlickGrid.
  // data    - A data Array for use in SlickGrid.
  //
  // Returns nothing.
  dp.loadTableView = function (columns, data) {
    var dialog = dp.$dialog;

    // Need to create the grid once the dialog is open for cells to render
    // correctly.
    dialog.dialog(dp.dialogOptions).one("dialogopen", function () {
      var element  = $(dp.template.html).appendTo(dialog);
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

      dialog.bind("dialogresizestop.data-preview", viewer.redraw);

      // Remove bindings when dialog is closed.
      dialog.bind("dialogbeforeclose", function () {
        dialog.unbind(".data-preview");
      });
    });
  };

  // Public: Sets up the dialog for displaying a full screen of data.
  //
  // dialogTitle - title for dialog window.
  //
  // Returns nothing.
  //
  dp.setupFullscreenDialog = function (dialogTitle) {
    var dialog = dp.$dialog, $window = $(window), timer;

    dialog.empty().dialog('option', 'title', 'View: ' + dialogTitle);

    // Ensure the lightbox always fills the screen.
    $window.bind('resize.data-preview', function () {
      clearTimeout(timer);
      timer = setTimeout(function () {
        dialog.dialog('option', {
          width:  $window.width()  - 20,
          height: $window.height() - 20
        });
        dialog.trigger('dialogresizestop');
      }, 100);
    });

    dialog.bind("dialogbeforeclose", function () {
      $window.unbind("resize.data-preview");
    });
  }

  // Public: Displays a smaller alert style dialog with an error message.
  //
  // error - An error object to display.
  //
  // Returns nothing.
  //
  dp.showError = function (error) {
    var _html = '<strong>' + $.trim(error.title) + '</strong><br />' + $.trim(error.message);
    dp.$dialog.html(_html).dialog(dp.errorDialogOptions);
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

    dp.loadTableView(tabular.columns, tabular.data);
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
