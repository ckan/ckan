var CKAN = CKAN || {};

CKAN.View = CKAN.View || {};
CKAN.Model = CKAN.Model || {};
CKAN.Utils = CKAN.Utils || {};
CKAN.Strings = CKAN.Strings || {};

/* TODO: set up properly */
CKAN.Strings.errorLoadingPreview = "Could not load preview";
CKAN.Strings.errorDataProxy = "DataProxy returned an error";
CKAN.Strings.errorDataStore = "DataStore returned an error";
CKAN.Strings.previewNotAvailableForDataType = "Preview not available for data type: ";

(function ($) {
  $(document).ready(function () {
    CKAN.DataPreview.loadPreviewDialog(preload_resource);
  });
}(jQuery));

/* ==================== */
/* == Data Previewer == */
/* ==================== */
CKAN.DataPreview = function ($, my) {
  my.jsonpdataproxyUrl = 'http://jsonpdataproxy.appspot.com/';
  my.dialogId = 'ckanext-datapreview';
  my.$dialog = $('#' + my.dialogId);

  // **Public: Loads a data previewer for an embedded page**
  //
  // Uses the provided reclineState to restore the Dataset.  Creates a single
  // view for the Dataset (the one defined by reclineState.currentView).  And
  // then passes the constructed Dataset, the constructed View, and the
  // reclineState into the DataExplorer constructor.
  my.loadEmbeddedPreview = function(resourceData, reclineState) {
    my.$dialog.html('<h4>Loading ... <img src="http://assets.okfn.org/images/icons/ajaxload-circle.gif" class="loading-spinner" /></h4>');

    // Restore the Dataset from the given reclineState.
    var dataset = recline.Model.Dataset.restore(reclineState);

    // Only create the view defined in reclineState.currentView.
    // TODO: tidy this up.
    var views = null;
    if (reclineState.currentView === 'grid') {
      views = [ {
        id: 'grid',
        label: 'Grid',
        view: new recline.View.SlickGrid({
          model: dataset,
          state: reclineState['view-grid']
        })
      }];
    } else if (reclineState.currentView === 'graph') {
      views = [ {
        id: 'graph',
        label: 'Graph',
        view: new recline.View.Graph({
          model: dataset,
          state: reclineState['view-graph']
        })
      }];
    } else if (reclineState.currentView === 'map') {
      views = [ {
        id: 'map',
        label: 'Map',
        view: new recline.View.Map({
          model: dataset,
          state: reclineState['view-map']
        })
      }];
    }

    // Finally, construct the DataExplorer.  Again, passing in the reclineState.
    var dataExplorer = new recline.View.MultiView({
      el: my.$dialog,
      model: dataset,
      state: reclineState,
      views: views
    });

  };

  // **Public: Creates a link to the embeddable page.
  //
  // For a given DataExplorer state, this function constructs and returns the
  // url to the embeddable view of the current dataexplorer state.
  my.makeEmbedLink = function(explorerState) {
    var state = explorerState.toJSON();
    state.state_version = 1;

    var queryString = '?';
    var items = [];
    $.each(state, function(key, value) {
      if (typeof(value) === 'object') {
        value = JSON.stringify(value);
      }
      items.push(key + '=' + escape(value));
    });
    queryString += items.join('&');
    return embedPath + queryString;
  };

  // **Public: Loads a data preview**
  //
  // Fetches the preview data object from the link provided and loads the
  // parsed data from the webstore displaying it in the most appropriate
  // manner.
  //
  // link - Preview button.
  //
  // Returns nothing.
  my.loadPreviewDialog = function(resourceData) {
    my.$dialog.html('<h4>Loading ... <img src="http://assets.okfn.org/images/icons/ajaxload-circle.gif" class="loading-spinner" /></h4>');

    function showError(msg){
      msg = msg || CKAN.Strings.errorLoadingPreview;
      return $('#ckanext-datapreview')
        .append('<div></div>')
        .addClass('alert alert-error fade in')
        .html(msg);
    }

    function initializeDataExplorer(dataset) {
      var views = [
        {
          id: 'grid',
          label: 'Grid',
          view: new recline.View.SlickGrid({
            model: dataset
          })
        },
        {
          id: 'graph',
          label: 'Graph',
          view: new recline.View.Graph({
            model: dataset
          })
        },
        {
          id: 'map',
          label: 'Map',
          view: new recline.View.Map({
            model: dataset
          })
        }
      ];

      var dataExplorer = new recline.View.MultiView({
        el: my.$dialog,
        model: dataset,
        views: views,
        config: {
          readOnly: true
        }
      });

      // Hide the fields control by default
      // (This should be done in recline!)
      $('.menu-right a[data-action="fields"]').click();

      // -----------------------------
      // Setup the Embed modal dialog.
      // -----------------------------

      // embedLink holds the url to the embeddable view of the current DataExplorer state.
      var embedLink = $('.embedLink');

      // embedIframeText contains the '<iframe>' construction, which sources
      // the above link.
      var embedIframeText = $('.embedIframeText');

      // iframeWidth and iframeHeight control the width and height parameters
      // used to construct the iframe, and are also used in the link.
      var iframeWidth = $('.iframe-width');
      var iframeHeight = $('.iframe-height');

      // Update the embedLink and embedIframeText to contain the updated link
      // and update width and height parameters.
      function updateLink() {
        return // FIXME what is this doing? disabled for now
        var link = my.makeEmbedLink(dataExplorer.state);
        var width = iframeWidth.val();
        var height = iframeHeight.val();
        link += '&width='+width+'&height='+height;

        // Escape '"' characters in {{link}} in order not to prematurely close
        // the src attribute value.
        embedIframeText.val($.mustache('<iframe frameBorder="0" width="{{width}}" height="{{height}}" src="{{link}}"></iframe>',
                                       {
                                         link: link.replace(/"/g, '&quot;'),
                                         width: width,
                                         height: height
                                       }));
        embedLink.attr('href', link);
      }

      // Bind changes to the DataExplorer, or the two width and height inputs
      // to re-calculate the url.
      dataExplorer.state.bind('change', updateLink);
      for (var i=0; i<dataExplorer.pageViews.length; i++) {
        dataExplorer.pageViews[i].view.state.bind('change', updateLink);
      }

      iframeWidth.change(updateLink);
      iframeHeight.change(updateLink);

      // Initial population of embedLink and embedIframeText
      updateLink();

      // Finally, since we have a DataExplorer, we can show the embed button.
      $('.preview-header .btn').show();

    }

    // 4 situations
    // a) webstore_url is active (something was posted to the datastore)
    // b) csv or xls (but not webstore)
    // c) can be treated as plain text
    // d) none of the above but worth iframing (assumption is
    // that if we got here (i.e. preview shown) worth doing
    // something ...)
    resourceData.formatNormalized = my.normalizeFormat(resourceData.format);

    resourceData.url  = my.normalizeUrl(resourceData.url);
    if (resourceData.formatNormalized === '') {
      var tmp = resourceData.url.split('/');
      tmp = tmp[tmp.length - 1];
      tmp = tmp.split('?'); // query strings
      tmp = tmp[0];
      var ext = tmp.split('.');
      if (ext.length > 1) {
        resourceData.formatNormalized = ext[ext.length-1];
      }
    }

    if (resourceData.webstore_url) {
      resourceData.url = '/api/data/' + resourceData.id;
      resourceData.backend =  'elasticsearch';
      var dataset = new recline.Model.Dataset(resourceData);
      var errorMsg = CKAN.Strings.errorLoadingPreview + ': ' + CKAN.Strings.errorDataStore;
      dataset.fetch()
        .done(function(dataset){
            initializeDataExplorer(dataset);
        })
        .fail(function(error){
          if (error.message) errorMsg += ' (' + error.message + ')';
          showError(errorMsg);
        });

    }
    else if (resourceData.formatNormalized in {'csv': '', 'xls': ''}) {
      // set format as this is used by Recline in setting format for DataProxy
      resourceData.format = resourceData.formatNormalized;
      resourceData.backend = 'dataproxy';
      var dataset = new recline.Model.Dataset(resourceData);
      var errorMsg = CKAN.Strings.errorLoadingPreview + ': ' +CKAN.Strings.errorDataProxy;
      dataset.fetch()
        .done(function(dataset){

          dataset.bind('query:fail', function(error) {
            $('#ckanext-datapreview .data-view-container').hide();
            $('#ckanext-datapreview .header').hide();
            $('.preview-header .btn').hide();
          });

          initializeDataExplorer(dataset);
          $('.recline-query-editor .text-query').hide();
        })
        .fail(function(error){
          if (error.message) errorMsg += ' (' + error.message + ')';
          showError(errorMsg);
        });
    }
    else if (resourceData.formatNormalized in {
        'rdf+xml': '',
        'owl+xml': '',
        'xml': '',
        'n3': '',
        'n-triples': '',
        'turtle': '',
        'plain': '',
        'atom': '',
        'tsv': '',
        'rss': '',
        'txt': ''
        }) {
      // HACK: treat as plain text / csv
      // pass url to jsonpdataproxy so we can load remote data (and tell dataproxy to treat as csv!)
      var _url = my.jsonpdataproxyUrl + '?type=csv&url=' + resourceData.url;
      my.getResourceDataDirect(_url, function(data) {
        my.showPlainTextData(data);
      });
    }
    else if (resourceData.formatNormalized in {'html':'', 'htm':''}
        ||  resourceData.url.substring(0,23)=='http://docs.google.com/') {
      // we displays a fullscreen dialog with the url in an iframe.
      my.$dialog.empty();
      var el = $('<iframe></iframe>');
      el.attr('src', resourceData.url);
      el.attr('width', '100%');
      el.attr('height', '100%');
      my.$dialog.append(el);
    }
    // images
    else if (resourceData.formatNormalized in {'png':'', 'jpg':'', 'gif':''}
        ||  resourceData.resource_type=='image') {
      // we displays a fullscreen dialog with the url in an iframe.
      my.$dialog.empty();
      var el = $('<img />');
      el.attr('src', resourceData.url);
      el.css('max-width', '100%');
      el.css('border', 'solid 4px black');
      my.$dialog.append(el);
    }
    else {
      // Cannot reliably preview this item - with no mimetype/format information,
      // can't guarantee it's not a remote binary file such as an executable.
      my.showError({
        title: CKAN.Strings.previewNotAvailableForDataType + resourceData.formatNormalized,
        message: ''
      });
    }
  };

  // Public: Requests the formatted resource data from the webstore and
  // passes the data into the callback provided.
  //
  // preview - A preview object containing resource metadata.
  // callback - A Function to call with the data when loaded.
  //
  // Returns nothing.
  my.getResourceDataDirect = function(url, callback) {
    // $.ajax() does not call the "error" callback for JSONP requests so we
    // set a timeout to provide the callback with an error after x seconds.
    var timeout = 5000;
    var timer = setTimeout(function error() {
      callback({
        error: {
          title: 'Request Error',
          message: 'Dataproxy server did not respond after ' + (timeout / 1000) + ' seconds'
        }
      });
    }, timeout);

    // have to set jsonp because webstore requires _callback but that breaks jsonpdataproxy
    var jsonp = '_callback';
    if (url.indexOf('jsonpdataproxy') != -1) {
      jsonp = 'callback';
    }

    // We need to provide the `cache: true` parameter to prevent jQuery appending
    // a cache busting `={timestamp}` parameter to the query as the webstore
    // currently cannot handle custom parameters.
    $.ajax({
      url: url,
      cache: true,
      dataType: 'jsonp',
      jsonp: jsonp,
      success: function(data) {
        clearTimeout(timer);
        callback(data);
      }
    });
  };

  // Public: Displays a String of data in a fullscreen dialog.
  //
  // data    - An object of parsed CSV data returned by the webstore.
  //
  // Returns nothing.
  my.showPlainTextData = function(data) {
    if(data.error) {
      my.showError(data.error);
    } else {
      var content = $('<pre></pre>');
      for (var i=0; i<data.data.length; i++) {
        var row = data.data[i].join(',') + '\n';
        content.append(my.escapeHTML(row));
      }
      my.$dialog.html(content);
    }
  };

  my.showError = function (error) {
    var _html = _.template(
        '<div class="alert alert-error"><strong><%= title %></strong><br /><%= message %></div>',
        error
    );
    my.$dialog.html(_html);
  };

  my.normalizeFormat = function(format) {
    var out = format.toLowerCase();
    out = out.split('/');
    out = out[out.length-1];
    return out;
  };

  my.normalizeUrl = function(url) {
    if (url.indexOf('https') === 0) {
      return 'http' + url.slice(5);
    } else {
      return url;
    }
  }

  // Public: Escapes HTML entities to prevent broken layout and XSS attacks
  // when inserting user generated or external content.
  //
  // string - A String of HTML.
  //
  // Returns a String with HTML special characters converted to entities.
  my.escapeHTML = function (string) {
    return string.replace(/&(?!\w+;|#\d+;|#x[\da-f]+;)/gi, '&amp;')
                 .replace(/</g, '&lt;').replace(/>/g, '&gt;')
                 .replace(/"/g, '&quot;')
                 .replace(/'/g, '&#x27')
                 .replace(/\//g,'&#x2F;');
  };


  // Export the CKANEXT object onto the window.
  $.extend(true, window, {CKANEXT: {}});
  CKANEXT.DATAPREVIEW = my;
  return my;
}(jQuery, CKAN.DataPreview || {});

