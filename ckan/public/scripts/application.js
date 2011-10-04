(function ($) {
  $(document).ready(function () {
    CKAN.Utils.setupUserAutocomplete($('input.autocomplete-user'));
    CKAN.Utils.setupAuthzGroupAutocomplete($('input.autocomplete-authzgroup'));
    CKAN.Utils.setupPackageAutocomplete($('input.autocomplete-dataset'));
    CKAN.Utils.setupTagAutocomplete($('input.autocomplete-tag'));
    $('input.autocomplete-format').live('keyup', function(){
      CKAN.Utils.setupFormatAutocomplete($(this));
    });
    CKAN.Utils.setupMarkdownEditor($('.markdown-editor .tabs a, .markdown-editor .markdown-preview'));
    // set up ckan js
    var config = {
      endpoint: '/'
    };
    var client = new CKAN.Client(config);
    // serious hack to deal with hacky code in ckanjs
    CKAN.UI.workspace = {
      client: client
    };

    var isDatasetNew = $('body.package.new').length > 0;
    if (isDatasetNew) {
      $('#save').val(CKAN.Strings.addDataset);
    }

    // Buttons with href-action should navigate when clicked
    $('input.href-action').click(function(e) {
      e.preventDefault();
      window.location = ($(e.target).attr('action'));
    });
    
    var isDatasetEdit = $('body.package.edit').length > 0;
    if (isDatasetEdit) {
      // Selectively enable the upload button
      var storageEnabled = $.inArray('storage',CKAN.plugins)>=0;
      if (storageEnabled) {
        $('div.resource-add li.upload-file').show();
      }

      // Set up hashtag nagivigation
      CKAN.Utils.setupDatasetEditNavigation();

      var _dataset = new CKAN.Model.Dataset(preload_dataset);
      var $el=$('form#dataset-edit');
      var view=new CKAN.View.DatasetEdit({
        model: _dataset,
        el: $el
      });
      view.render();
    }
  });
}(jQuery));

var CKAN = CKAN || {};

CKAN.Utils = function($, my) {
  // Attach dataset autocompletion to provided elements
  //
  // Requires: jquery-ui autocomplete
  my.setupPackageAutocomplete = function(elements) {
    elements.autocomplete({
      minLength: 0,
      source: function(request, callback) {
        var url = '/dataset/autocomplete?q=' + request.term;
        $.ajax({
          url: url,
          success: function(data) {
            // atm is a string with items broken by \n and item = title (name)|name
            var out = [];
            var items = data.split('\n');
            $.each(items, function(idx, value) {
              var _tmp = value.split('|');
              var _newItem = {
                label: _tmp[0],
                value: _tmp[1]
              };
              out.push(_newItem);
            });
            callback(out);
          }
        });
      }
      , select: function(event, ui) {
        var input_box = $(this);
        input_box.val('');
        var parent_dd = input_box.parent('dd');
        var old_name = input_box.attr('name');
        var field_name_regex = /^(\S+)__(\d+)__(\S+)$/;
        var split = old_name.match(field_name_regex);

        var new_name = split[1] + '__' + (parseInt(split[2]) + 1) + '__' + split[3]

        input_box.attr('name', new_name)
        input_box.attr('id', new_name)

        parent_dd.before(
          '<input type="hidden" name="' + old_name + '" value="' + ui.item.value + '">' +
          '<dd>' + ui.item.label + '</dd>'
        );
      }
    });
  };

  // Attach tag autocompletion to provided elements
  //
  // Requires: jquery-ui autocomplete
  my.setupTagAutocomplete = function(elements) {
    elements
      // don't navigate away from the field on tab when selecting an item
      .bind( "keydown", function( event ) {
        if ( event.keyCode === $.ui.keyCode.TAB &&
            $( this ).data( "autocomplete" ).menu.active ) {
          event.preventDefault();
        }
      })
      .autocomplete({
        minLength: 1,
        source: function(request, callback) {
          // here request.term is whole list of tags so need to get last
          var _realTerm = request.term.split(' ').pop();
          var url = '/api/2/util/tag/autocomplete?incomplete=' + _realTerm;
          $.getJSON(url, function(data) {
            // data = { ResultSet: { Result: [ {Name: tag} ] } } (Why oh why?)
            var tags = $.map(data.ResultSet.Result, function(value, idx) {
              return value.Name;
            });
            callback(
              $.ui.autocomplete.filter(tags, _realTerm)
            );
          });
        },
        focus: function() {
          // prevent value inserted on focus
          return false;
        },
        select: function( event, ui ) {
          var terms = this.value.split(' ');
          // remove the current input
          terms.pop();
          // add the selected item
          terms.push( ui.item.value );
          // add placeholder to get the comma-and-space at the end
          terms.push( "" );
          this.value = terms.join( " " );
          return false;
        }
    });
  };

  // Attach tag autocompletion to provided elements
  //
  // Requires: jquery-ui autocomplete
  my.setupFormatAutocomplete = function(elements) {
    elements.autocomplete({
      minLength: 1,
      source: function(request, callback) {
        var url = '/api/2/util/resource/format_autocomplete?incomplete=' + request.term;
        $.getJSON(url, function(data) {
          // data = { ResultSet: { Result: [ {Name: tag} ] } } (Why oh why?)
          var formats = $.map(data.ResultSet.Result, function(value, idx) {
            return value.Format;
          });
          callback(formats);
        });
      }
    });
  };

  // Attach user autocompletion to provided elements
  //
  // Requires: jquery-ui autocomplete
  my.setupUserAutocomplete = function(elements) {
    elements.autocomplete({
      minLength: 2,
      source: function(request, callback) {
        var url = '/api/2/util/user/autocomplete?q=' + request.term;
        $.getJSON(url, function(data) {
          $.each(data, function(idx, userobj) {
            var label = userobj.name;
            if (userobj.fullname) {
              label += ' [' + userobj.fullname + ']';
            }
            userobj.label = label;
            userobj.value = userobj.name;
          });
          callback(data);
        });
      }
    });
  };

  // Attach authz group autocompletion to provided elements
  //
  // Requires: jquery-ui autocomplete
  my.setupAuthzGroupAutocomplete = function(elements) {
    elements.autocomplete({
      minLength: 2,
      source: function(request, callback) {
        var url = '/api/2/util/authorizationgroup/autocomplete?q=' + request.term;
        $.getJSON(url, function(data) {
          $.each(data, function(idx, userobj) {
            var label = userobj.name;
            userobj.label = label;
            userobj.value = userobj.name;
          });
          callback(data);
        });
      }
    });
  };

  my.setupMarkdownEditor = function(elements) {
    // Markdown editor hooks
    elements.live('click', function(e) {
      e.preventDefault();
      var $el = $(e.target);
      var action = $el.attr('action') || 'write';
      // Extract neighbouring elements
      var div=$el.closest('.markdown-editor')
      div.find('.tabs a').removeClass('selected');
      div.find('.tabs a[action='+action+']').addClass('selected');
      var textarea = div.find('.markdown-input');
      var preview = div.find('.markdown-preview');
      // Toggle the preview
      if (action=='preview') {
        raw_markdown=textarea.val();
        preview.html("<em>"+CKAN.Strings.loading+"<em>");
        $.post("/api/util/markdown", { q: raw_markdown },
          function(data) { preview.html(data); }
        );
        preview.width(textarea.width())
        preview.height(textarea.height())
        textarea.hide();
        preview.show();
      } else {
        textarea.show();
        preview.hide();
        textarea.focus();
      }
      return false;
    });
  };


  // Show/hide fieldset sections from the edit dataset form. 
  my.setupDatasetEditNavigation = function() {

    function showSection(sectionToShowId) {
      $('.dataset fieldset').hide();
      $('.dataset fieldset#'+sectionToShowId).show();
      $('.edit-form-navigation li a').removeClass('active');
      $('.edit-form-navigation li a[href=#section-'+sectionToShowId+']').addClass('active');
      window.location.hash = 'section-'+sectionToShowId;
    }

    // Set up initial form state
    // Prefix="#section-"
    var initialSection = window.location.hash.slice(9) || 'basic-information';
    showSection(initialSection);
    
    // Adjust form state on click
    $('.edit-form-navigation li a').live('click', function(e) {
      var $el = $(e.target);
      // Prefix="#section-"
      var showMe = $el.attr('href').slice(9);
      showSection(showMe);
      return false;
    });  
  };

  // Name slug generator for $name element using $title element
  //
  // Also does nice things like show errors if name not available etc
  //
  // Usage: CKAN.Utils.PackageSlugCreator.create($('#my-title'), $('#my-name'))
  my.PackageSlugCreator = (function() {
    // initialize function
    // 
    // args: $title and $name input elements
    function SlugCreator($title, $name) {
      this.name_field = $name;
      this.title_field = $title;
      // Keep a variable where we can store whether the name field has been
      // directly modified by the user or not. If it has, we should no longer
      // fetch updates.
      this.name_changed = false;
      // url for slug api (we need api rather than do it ourself because we check if available)
      this.url = '/api/2/util/dataset/create_slug';
      // Add a new element where the validity of the dataset name can be displayed
      this.name_field.parent().append('<div id="dataset_name_valid_msg"></div>');
      this.title_field.blur(this.title_change_handler())
      this.title_field.keyup(this.title_change_handler())
      this.name_field.keyup(this.name_change_handler());
      this.name_field.blur(this.name_blur_handler());
    }

    SlugCreator.create = function($title, $name) {
      return new SlugCreator($title, $name);
    }

    SlugCreator.prototype.title_change_handler = function() {
      var self = this;
      return function() {
        if (!self.name_changed && self.title_field.val().replace(/^\s+|\s+$/g, '')) {
          self.update(self.title_field.val(), function(data) {self.name_field.val(data.name)});
        }
      }
    }

    SlugCreator.prototype.name_blur_handler = function() {
      var self = this;
      return function() {
        // Reset if the name is emptied
        if (!self.name_field.val().replace(/^\s+|\s+$/g, '')){
          self.name_changed = false;
          $('#dataset_name_valid_msg').html('');
        } else {
          self.update(self.name_field.val(), function(data) {
              self.name_field.val(data.name)
          });
        }
      };
    }

    SlugCreator.prototype.name_change_handler = function() {
      var self = this;
      return function() {
        // Reset if the name is emptied
        if (!self.name_field.val().replace(/^\s+|\s+$/g, '')){
          self.name_changed = false;
          $('#dataset_name_valid_msg').html('');
        } else {
          self.name_changed = true;
          self.update(self.name_field.val(), function(data) {
            if (self.name_field.val().length >= data.name) {
                self.name_field.val(data.name);
            }
          });
        }
      };
    }

    // Create a function for fetching the value and updating the result
    SlugCreator.prototype.perform_update = function(value, on_success){
      var self = this;
      $.ajax({
        url: self.url,
        data: 'title=' + value,
        dataType: 'jsonp',
        type: 'get',
        jsonpCallback: 'callback',
        success: function (data) {
          if (on_success) {
            on_success(data);
          }
          var valid_msg = $('#dataset_name_valid_msg');
          if (data.valid) {
            valid_msg.html('<span style="font-weight: bold; color: #0c0">'+CKAN.Strings.datasetNameAvailable+'</span>');
          } else {
            valid_msg.html('<span style="font-weight: bold; color: #c00">'+CKAN.Strings.datasetNameNotAvailable+'</span>');
          }
        }
      });
    }

    // We only want to perform the update if there hasn't been a change for say 200ms
    var timer = null;
    SlugCreator.prototype.update = function(value, on_success) {
      var self = this;
      if (this.timer) {
        clearTimeout(this.timer)
      };
      this.timer = setTimeout(function () {
        self.perform_update(value, on_success)
      }, 200);
    }

    return SlugCreator;
  })();


  return my;
}(jQuery, CKAN.Utils || {});


CKAN.View.DatasetEdit = Backbone.View.extend({
  initialize: function() {
    _.bindAll(this, 'render');

    var boundToUnload = false;
    this.el.change(function() {
      if (!boundToUnload) {
        boundToUnload = true;
        window.onbeforeunload = function () { 
          return CKAN.Strings.youHaveUnsavedChanges; 
        };
      }
    });
    this.el.submit(function() {
      // Don't stop us leaving
      window.onbeforeunload = null;
    });

    // Tabbed view for adding resources
    var $el=this.el.find('.resource-add');
    this.addView=new CKAN.View.ResourceAdd({
      collection: this.model.get('resources'),
      el: $el
    });

    // Table for editing resources
    var $el=this.el.find('.resource-table.edit');
    this.resourceList=new CKAN.View.ResourceEditList({
      collection: this.model.get('resources'),
      el: $el
    });

    this.render();
  },


  render: function() {
    this.addView.render();
    this.resourceList.render();
  },

  events: {
  }

});


CKAN.View.ResourceEditList = Backbone.View.extend({
  initialize: function() {
    _.bindAll(this, 'render', 'addRow');
    this.collection.bind('add', this.addRow);
  },

  render: function() {
    var self = this;

    // Have to trash entire content; some stuff was there on page load
    this.el.find('tbody').empty();
    this.collection.each(this.addRow);

    if (this.collection.isEmpty()) {
      $tr = $('<tr />').addClass('table-empty');
      $tr.html('<td></td><td colspan="4">'+CKAN.Strings.bracketsNone+'</td>');
      this.el.find('tbody').append($tr);
    }
  },

  nextIndex: function() {
    var maxId=-1;
    this.el.find('input').each(function(idx,input) {
      var splitName=$(input).attr('name').split('__');
      if (splitName.length>1) {
        var myId = parseInt(splitName[1])
        maxId = Math.max(myId, maxId);
      }
    });
    return maxId+1;
  },

  addRow: function(resource) {
    // Strip placeholder row
    this.el.find('tr.table-empty').remove();

    // TODO tidy up so the view creates its own elements
    var $tr = $('<tr />');

    // Captured by an inner function
    var self = this;

    this.el.find('tbody.resource-table').append($tr);
    var _view = new CKAN.View.ResourceEdit({
      model: resource,
      el: $tr,
      position: this.nextIndex(),
      deleteResource: function() {
        // Passing down a capture to remove the resource
        $tr.remove();
        
        self.collection.remove(resource);
        if (self.collection.isEmpty()) {
          self.render();
        }
      }
    });
    _view.render();
  },

  events: {
  }
});

CKAN.View.ResourceEdit = Backbone.View.extend({
  initialize: function() {
    _.bindAll(this, 'render', 'toggleExpanded');
    var self = this;
    this.model.bind('change', function() { self.hasChanged=true; });
    this.model.bind('change', this.render());
    this.position = this.options.position;

    this.expanded = this.model.isNew();
    this.hasChanged = this.model.isNew();
    this.animate = this.model.isNew();
  },

  render: function() {
    var tmplData = {
      resource: this.model.toTemplateJSON(),
      num: this.position
    };
    var $newRow = $.tmpl(CKAN.Templates.resourceEntry, tmplData);
    this.el.html($newRow);

    if (this.expanded) {
      this.el.find('a.resource-expand-link').hide();
      this.el.find('.resource-summary').hide();
      if (this.animate) {
        this.el.find('.resource-expanded .inner').hide();
        this.el.find('.resource-expanded .inner').show('slow');
      }
    }
    else {
      this.el.find('a.resource-collapse-link').hide();
      this.el.find('.resource-expanded').hide();
    }

    if (!this.hasChanged) {
      this.el.find('img.resource-is-changed').hide();
    }
    this.animate = false;
  },

  events: {
    'click a.resource-expand-link': 'toggleExpanded',
    'click a.resource-collapse-link': 'toggleExpanded',
    'click .delete-resource': 'clickDelete'
  },

  clickDelete: function(e) {
    e.preventDefault();
    this.options.deleteResource();
  },

  saveData: function() {
    this.model.set(this.getData(), {
      error: function(model, error) {
        var msg = CKAN.Strings.failedToSave;
        msg += JSON.stringify(error);
        alert(msg);
      }
    });
    return false;
  },

  getData: function() {
    var _data = $(this.el).find('input').serializeArray();
    modelData = {};
    $.each(_data, function(idx, value) {
      modelData[value.name.split('__')[2]] = value.value
    });
    return modelData;
  },

  toggleExpanded: function(e) {
    e.preventDefault();

    this.expanded = !this.expanded;
    this.animate = true;
    // Closing the form; update the model fields
    if (!this.expanded) {
      this.saveData();
      // Model might not have changed
      this.render();
    } else {
      this.render();
    }
  }

});

CKAN.View.ResourceAdd = Backbone.View.extend({
  initialize: function() {
    _.bindAll(this, 'render', 'addNewResource', 'reset');
  },

  render: function() {
  },

  events: {
    'click .action-resource-tab': 'clickAdd',
    'click input[name=reset]': 'reset'
  },

  reset: function() {
    this.el.find('.tabs a').removeClass('selected');
    if (this.subView != null) {
      this.subView.remove();
      this.subView = null;
    }
    return false;
  },

  clickAdd: function(e) {
    e.preventDefault();

    this.reset();

    var action = $(e.target).attr('action');
    this.el.find('.tabs a').removeClass('selected');
    this.el.find('.tabs a[action='+action+']').addClass('selected');

    var $subPane = $('<div />').addClass('resource-add-subpane');
    this.el.append($subPane);

    var tempResource = new CKAN.Model.Resource({});

    tempResource.bind('change', this.addNewResource);
    // Open sub-pane
    if (action=='upload-file') {
      this.subView = new CKAN.View.ResourceUpload({
        el: $subPane,
        model: tempResource,
        // TODO: horrible reverse depedency ...
        client: CKAN.UI.workspace.client
      });
    }
    else if (action=='link-file' || action=='link-api') {
      this.subView = new CKAN.View.ResourceAddLink({
        el: $subPane,
        model: tempResource,
        mode: (action=='link-file')? 'file' : 'api',
        // TODO: horrible reverse depedency ...
        client: CKAN.UI.workspace.client
      });
    }
    this.subView.render();
  },

  addNewResource: function(tempResource) {
    // Deep-copy the tempResource we had bound to
    var resource=new CKAN.Model.Resource(tempResource.toJSON());

    this.collection.add(resource);
    this.reset();
  }
});

CKAN.View.ResourceAddLink = Backbone.View.extend({
  initialize: function(options) {
    _.bindAll(this, 'render');
    this.mode = options.mode;
  },

  render: function() {
    if (this.mode=='file') {
      var tmpl = $.tmpl(CKAN.Templates.resourceAddLinkFile);
    }
    else if (this.mode=='api') {
      var tmpl = $.tmpl(CKAN.Templates.resourceAddLinkApi);
    }
    $(this.el).html(tmpl);
    return this;
  },

  events: {
    'submit form': 'setResourceInfo',
  },

  setResourceInfo: function(e) {
    e.preventDefault();
    var urlVal=this.el.find('input[name=url]').val();
    this.model.set({url: urlVal, resource_type: this.mode})
  }
});


