// recline preview module
this.ckan.module('reclinepreview', function (jQuery, _) {
  return {
    options: {
      i18n: {
        errorLoadingPreview: "Could not load view",
        errorDataProxy: "DataProxy returned an error",
        errorDataStore: "DataStore returned an error",
        previewNotAvailableForDataType: "View not available for data type: "
      },
      site_url: ""
    },

    initialize: function () {
      jQuery.proxyAll(this, /_on/);
      this.options.resource = JSON.parse(this.options.resource);
      this.options.resourceView = JSON.parse(this.options.resourceView);
      this.el.ready(this._onReady);
      // hack to make leaflet use a particular location to look for images
      L.Icon.Default.imagePath = this.options.site_url + 'vendor/leaflet/0.4.4/images';
    },

    _onReady: function() {
      var resourceData = this.options.resource,
          resourceView = this.options.resourceView;

      this.loadView(resourceData, resourceView);
    },

    loadView: function (resourceData, reclineView) {
      var self = this;

      function showError(msg){
        msg = msg || _('error loading preview');
        window.parent.ckan.pubsub.publish('data-viewer-error', msg);
      }

      resourceData.url  = this.normalizeUrl(resourceData.url);
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

      var errorMsg, dataset;

      resourceData.backend =  'ckan';
      resourceData.endpoint = jQuery('body').data('site-root') + 'api';

      dataset = new recline.Model.Dataset(resourceData);
      dataset.query({
        "from": reclineView.offset || 0,
        "size": reclineView.limit || 100
      });

      errorMsg = this.options.i18n.errorLoadingPreview + ': ' + this.options.i18n.errorDataStore;
      dataset.fetch()
        .done(function(dataset){
            self.initializeView(dataset, reclineView);
        })
        .fail(function(error){
          if (error.message) errorMsg += ' (' + error.message + ')';
          showError(errorMsg);
        });
    },

    initializeView: function (dataset, reclineView) {
      var view;

      if(reclineView.view_type === "recline_graph") {
        var state = {
          "graphType": reclineView.graph_type,
          "group": reclineView.group,
          "series": [reclineView.series]
        };
        view = new recline.View.Graph({model: dataset, state: state});
      } else if(reclineView.view_type === "recline_map") {
        var state = {
          geomField: null,
          latField: null,
          lonField: null,
          autoZoom: Boolean(reclineView.auto_zoom),
          cluster: Boolean(reclineView.cluster_markers)
        };

        if(reclineView.map_field_type === "geojson") {
          state.geomField = reclineView.geojson_field;
        } else {
          state.latField = reclineView.latitude_field;
          state.lonField = reclineView.longitude_field;
        }

        view = new recline.View.Map({model: dataset, state: state});
      } else {
        // default to Grid
        view = new recline.View.SlickGrid({model: dataset});
        this.pager = new recline.View.Pager({model: view.model.queryState});
        $('#recline-controls').append(this.pager.el);
      }

      this.el.replaceWith(view.el);
      view.visible = true;
      view.render();

      if(reclineView.view_type === "recline_graph") {
        view.redraw();
      }
    },

    normalizeUrl: function (url) {
      if (url.indexOf('https') === 0) {
        return 'http' + url.slice(5);
      } else {
        return url;
      }
    }
  };
});
