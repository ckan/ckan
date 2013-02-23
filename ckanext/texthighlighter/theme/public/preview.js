// json preview module
ckan.module('texthighlighter', function (jQuery, _) {
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
			  language: 'json', 
			  dataConverter: function (data) { return JSON.stringify(data, null, 2); }, 
			  dataType: 'json'},
		  jsonp: {
			  contentType: 'application/javascript',
			  language: 'javascript',
			  dataType: 'jsonp'
		  },
		  xml: {
			  contentType: 'text/xml',
			  language: 'xml',
			  dataType: 'text'},
		  txt: {
			  contentType: 'text/plain',
			  language: '',
			  dataType: 'text'}
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
	   	  var data = p.dataConverter ? p.dataConverter(data) : data;
		  var highlighted;

		  if (p.language) {
			highlighted = hljs.highlight(p.language, data, true).value;
		  }
		  else {
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
