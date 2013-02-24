// json preview module
ckan.module('textpreview', function (jQuery, _) {
  return {
    options: {
      i18n: {
        error: _('An error occurred: %(text)s %(error)s')
      }
    },
    initialize: function () {
      var parameters = {
        json: {
          contentType: 'application/json',
          dataType: 'json',
          dataConverter: function (data) { return JSON.stringify(data, null, 2); },
          language: 'json'
        },
        jsonp: {
          contentType: 'application/javascript',
          dataType: 'jsonp',
          language: 'javascript'
        },
        xml: {
          contentType: 'text/xml',
          dataType: 'text',
          language: 'xml'
        },
        txt: {
          contentType: 'text/plain',
          dataType: 'text',
          language: ''
        }
      };
      parameters['text/plain'] = parameters.txt;
      parameters['rdf'] = parameters.xml;

      var self = this;
      var p = parameters[preload_resource['format'].toLowerCase()];

      jQuery.ajax(preload_resource['url'], {
        type: 'GET',
        async: false,
        dataType: p.dataType,
        success: function(data, textStatus, jqXHR) {
          var converted = p.dataConverter ? p.dataConverter(data) : data;
          var highlighted;

          if (p.language) {
            highlighted = hljs.highlight(p.language, converted, true).value;
          } else {
            highlighted = '<pre>' + converted + '</pre>';
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
