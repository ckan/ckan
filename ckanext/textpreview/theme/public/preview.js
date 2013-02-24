// json preview module
ckan.module('textpreview', function (jQuery, _) {
  return {
    options: {
      i18n: {
        error: _('An error occurred: %(text)s %(error)s')
      },
      parameters: {
        json: {
          contentType: 'application/json',
          dataType: 'json',
          dataConverter: function (data) { return JSON.stringify(data, null, 2); },
          language: 'json'
        },
        jsonp: {
          contentType: 'application/javascript',
          dataType: 'jsonp',
          dataConverter: function (data) { return JSON.stringify(data, null, 2); },
          language: 'json'
        },
        xml: {
          contentType: 'text/xml',
          dataType: 'text',
          language: 'xml'
        },
        text: {
          contentType: 'text/plain',
          dataType: 'text',
          language: ''
        }
      }
    },
    initialize: function () {
      var self = this;
      var format = preload_resource['format'].toLowerCase();

      var TEXT_FORMATS = ['text/plain', 'txt', 'plain'];
      var XML_FORMATS = ['xml', 'rdf', 'rdf+xm', 'owl+xml', 'atom', 'rss'];
      var JSON_FORMATS = ['json'];
      var JSONP_FORMATS = ['jsonp'];

      var p;

      if (JSON_FORMATS.indexOf(format) !== -1) {
        p = this.options.parameters.json;
      } else if (JSONP_FORMATS.indexOf(format) !== -1) {
        p = this.options.parameters.jsonp;
      } else if(XML_FORMATS.indexOf(format) !== -1) {
        p = this.options.parameters.xml;
      } else {
        p = this.options.parameters.text;
      }

      jQuery.ajax(preload_resource['url'], {
        type: 'GET',
        async: false,
        contentType: p.contentType,
        dataType: p.dataType,
        success: function(data, textStatus, jqXHR) {
          data = p.dataConverter ? p.dataConverter(data) : data;
          var highlighted;

          if (p.language) {
            highlighted = hljs.highlight(p.language, data, true).value;
          } else {
            highlighted = '<pre>' + data + '</pre>';
          }

          self.el.html(highlighted);
        },
        error: function(jqXHR, textStatus, errorThrown) {
          self.el.html(self.i18n('error', {text: textStatus, error: errorThrown}));
        }
      });
    }
  };
});
