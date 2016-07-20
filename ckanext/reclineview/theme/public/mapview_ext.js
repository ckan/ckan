/**
 * Author: Khalegh Mamakani @ Highway Three Solutions Inc.
 *
 * Copyright 2016 Province of British Columbia
**/
(function (ckan, jQuery) {

  ckan.MapView = recline.View.Map.extend({

    initialize : function (options) {
        this.mapConfig = options.mapConfig;
        recline.View.Map.prototype.initialize.apply(this, [options])
    },

    _setupMap: function(){

      var self = this;

      var mapConfig = this.mapConfig;
      /*
      If no map configuration is provided use recline default map tiles.
      */
      if ((typeof mapConfig === 'undefined') || jQuery.isEmptyObject(mapConfig)) {
        recline.View.Map.prototype._setupMap.apply(this);
        return;
      }

      var isHttps = window.location.href.substring(0, 5).toLowerCase() === 'https';

      var leafletMapOptions = this.leafletMapOptions || {};
      var leafletBaseLayerOptions = jQuery.extend(this.leafletBaseLayerOptions, {
                maxZoom: 18
          });

      this.map = new L.Map(this.$map.get(0));

      var baseLayerUrl = '';

      if (mapConfig.type == 'mapbox') {
          // MapBox base map
          if (!mapConfig['mapbox.map_id'] || !mapConfig['mapbox.access_token']) {
            throw '[CKAN Map Widgets] You need to provide a map ID ([account].[handle]) and an access token when using a MapBox layer. ' +
                  'See http://www.mapbox.com/developers/api-overview/ for details';
          }

          baseLayerUrl = '//{s}.tiles.mapbox.com/v4/' + mapConfig['mapbox.map_id'] + '/{z}/{x}/{y}.png?access_token=' + mapConfig['mapbox.access_token'];
          leafletBaseLayerOptions.handle = mapConfig['mapbox.map_id'];
          leafletBaseLayerOptions.subdomains = mapConfig.subdomains || 'abcd';
          leafletBaseLayerOptions.attribution = mapConfig.attribution || 'Data: <a href="http://osm.org/copyright" target="_blank">OpenStreetMap</a>, Design: <a href="http://mapbox.com/about/maps" target="_blank">MapBox</a>';
      } else if (mapConfig.type == 'custom') {
          // Custom XYZ layer
          baseLayerUrl = mapConfig['custom.url'];
          if (mapConfig.subdomains) leafletBaseLayerOptions.subdomains = mapConfig.subdomains;
          if (mapConfig.tms) leafletBaseLayerOptions.tms = mapConfig.tms;
          leafletBaseLayerOptions.attribution = mapConfig.attribution;
      } else {

          // MapQuest OpenStreetMap base map
          if (isHttps) {
            baseLayerUrl = '//otile{s}-s.mqcdn.com/tiles/1.0.0/osm/{z}/{x}/{y}.png';
          } else {
            baseLayerUrl = '//otile{s}.mqcdn.com/tiles/1.0.0/osm/{z}/{x}/{y}.png';
          }
          leafletBaseLayerOptions.subdomains = mapConfig.subdomains || '1234';
          leafletBaseLayerOptions.attribution = mapConfig.attribution || 'Map data &copy; OpenStreetMap contributors, Tiles Courtesy of <a href="http://www.mapquest.com/" target="_blank">MapQuest</a> <img src="//developer.mapquest.com/content/osm/mq_logo.png">';
      }

      var baseLayer = new L.TileLayer(baseLayerUrl, leafletBaseLayerOptions);
      this.map.addLayer(baseLayer);

      this.markers = new L.MarkerClusterGroup(this._clusterOptions);

      // rebind this (as needed in e.g. default case above)
      this.geoJsonLayerOptions.pointToLayer =  _.bind(
          this.geoJsonLayerOptions.pointToLayer,
          this);
      this.features = new L.GeoJSON(null, this.geoJsonLayerOptions);

      var ckanext_reclineview_map_center = JSON.parse(mapConfig.center || '[0, 0]');
      var ckanext_reclineview_map_zoom = parseInt(mapConfig.zoom || '2');

      this.map.setView(ckanext_reclineview_map_center, ckanext_reclineview_map_zoom);

      this.mapReady = true;
    }

  });

})(this.ckan, this.jQuery);
