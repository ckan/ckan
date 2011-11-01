(function ($) {
  $(document).ready(function () {
    CKAN.Utils.setupUserAutocomplete($('input.autocomplete-user'));
    CKAN.Utils.setupAuthzGroupAutocomplete($('input.autocomplete-authzgroup'));
    CKAN.Utils.setupPackageAutocomplete($('input.autocomplete-dataset'));
    CKAN.Utils.setupTagAutocomplete($('input.autocomplete-tag'));
    $('input.autocomplete-format').live('keyup', function(){
      CKAN.Utils.setupFormatAutocomplete($(this));
    });
    CKAN.Utils.setupMarkdownEditor($('.markdown-editor'));
    // set up ckan js
    var config = {
      endpoint: '/'
    };
    var client = new CKAN.Client(config);
    // serious hack to deal with hacky code in ckanjs
    CKAN.UI.workspace = {
      client: client
    };

    var isDatasetView = $('body.package.read').length > 0;
    if (isDatasetView) {
      var _dataset = new CKAN.Model.Dataset(preload_dataset);
      CKANEXT.DATAPREVIEW.setupDataPreview(_dataset);
    }

    var isDatasetNew = $('body.package.new').length > 0;
    if (isDatasetNew) {
      // Set up magic URL slug editor
      CKAN.Utils.setupUrlEditor('package');
      $('#save').val(CKAN.Strings.addDataset);
      $("#title").focus();
    }
    var isGroupNew = $('body.group.new').length > 0;
    if (isGroupNew) {
      // Set up magic URL slug editor
      CKAN.Utils.setupUrlEditor('group');
      $('#save').val(CKAN.Strings.addGroup);
      $("#title").focus();
    }

    // Buttons with href-action should navigate when clicked
    $('input.href-action').click(function(e) {
      e.preventDefault();
      window.location = ($(e.target).attr('action'));
    });
    
    var isDatasetEdit = $('body.package.edit').length > 0;
    if (isDatasetEdit) {
      CKAN.Utils.setupUrlEditor('package',readOnly=true);
      // Selectively enable the upload button
      var storageEnabled = $.inArray('storage',CKAN.plugins)>=0;
      if (storageEnabled) {
        $('li.js-upload-file').show();
      }

      // Set up hashtag nagivigation
      CKAN.Utils.setupDatasetEditNavigation();

      var _dataset = new CKAN.Model.Dataset(preload_dataset);
      var $el=$('form#dataset-edit');
      var view=new CKAN.View.DatasetEditForm({
        model: _dataset,
        el: $el
      });
      view.render();
    }
    var isGroupEdit = $('body.group.edit').length > 0;
    if (isGroupEdit) {
      CKAN.Utils.setupUrlEditor('group',readOnly=true);
    }
  });
}(jQuery));

var CKAN = CKAN || {};

CKAN.Utils = function($, my) {

  my.flashMessage = function(msg, category) {
    if (!category) {
      category = 'info';
    }
    var messageDiv = $('<div />').html(msg).addClass(category).hide();
    $('.flash-messages').append(messageDiv);
    messageDiv.show(1200);
  };

  my.bindInputChanges = function(input, callback) {
    input.keyup(callback);
    input.keydown(callback);
    input.keypress(callback);
    input.change(callback);
  };

  my.setupUrlEditor = function(slugType,readOnly) {
    // Page elements to hook onto
    var titleInput = $('.js-title');
    var urlText = $('.js-url-text');
    var urlSuffix = $('.js-url-suffix');
    var urlInput = $('.js-url-input');
    var validMsg = $('.js-url-is-valid');

    var api_url = '/api/2/util/is_slug_valid';
    // (make length less than max, in case we need a few for '_' chars to de-clash slugs.)
    var MAX_SLUG_LENGTH = 90;

    var titleChanged = function() {
      var lastTitle = "";
      var regexToHyphen = [ new RegExp('[ .:/_]', 'g'), 
                        new RegExp('[^a-zA-Z0-9-_]', 'g'), 
                        new RegExp('-+', 'g')];
      var regexToDelete = [ new RegExp('^-*', 'g'), 
                        new RegExp('-*$', 'g')];

      var titleToSlug = function(title) {
        var slug = title;
        $.each(regexToHyphen, function(idx,regex) { slug = slug.replace(regex, '-'); });
        $.each(regexToDelete, function(idx,regex) { slug = slug.replace(regex, ''); });
        slug = slug.toLowerCase();

        if (slug.length<MAX_SLUG_LENGTH) {
            slug=slug.substring(0,MAX_SLUG_LENGTH);
        }
        return slug;
      };

      // Called when the title changes
      return function() {
        var title = titleInput.val();
        if (title == lastTitle) return;
        lastTitle = title;

        slug = titleToSlug(title);
        urlInput.val(slug);
        urlInput.change();
      };
    }();

    var urlChanged = function() {
      var timer = null;

      var checkSlugValid = function(slug) {
        $.ajax({
          url: api_url,
          data: 'type='+slugType+'&slug=' + slug,
          dataType: 'jsonp',
          type: 'get',
          jsonpCallback: 'callback',
          success: function (data) {
            if (data.valid) {
              validMsg.html('<span style="font-weight: bold; color: #0c0">'+CKAN.Strings.urlIsAvailable+'</span>');
            } else {
              validMsg.html('<span style="font-weight: bold; color: #c00">'+CKAN.Strings.urlIsNotAvailable+'</span>');
            }
          }
        });
      }

      return function() {
        slug = urlInput.val();
        urlSuffix.html('<span>'+slug+'</span>');
        validMsg.html('<span style="color: #777;">'+CKAN.Strings.checking+'</span>');
        if (timer) clearTimeout(timer);
        timer = setTimeout(function () {
          checkSlugValid(slug);
        }, 200);
      };
    }();

    if (readOnly) {
      slug = urlInput.val();
      urlSuffix.html('<span>'+slug+'</span>');
    }
    else {
      var editLink = $('.js-url-editlink');
      editLink.show();
      // Hook title changes to the input box
      my.bindInputChanges(titleInput, titleChanged);
      my.bindInputChanges(urlInput, urlChanged);
      // Set up the form
      urlChanged();

      editLink.live('click',function(e) {
        e.preventDefault();
        $('.js-url-viewmode').hide();
        $('.js-url-editmode').show();
        urlInput.select();
        urlInput.focus();
      });
    }
  }

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

  my.setupMarkdownEditor = function(markdownEditor) {
    // Markdown editor hooks
    markdownEditor.find('button, div.markdown-preview').live('click', function(e) {
      e.preventDefault();
      var $target = $(e.target);
      // Extract neighbouring elements
      var markdownEditor=$target.closest('.markdown-editor')
      markdownEditor.find('button').removeClass('depressed');
      var textarea = markdownEditor.find('.markdown-input');
      var preview = markdownEditor.find('.markdown-preview');
      // Toggle the preview
      if ($target.is('.js-markdown-preview')) {
        $target.addClass('depressed');
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
        markdownEditor.find('.js-markdown-edit').addClass('depressed');
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
      $('.dataset-edit-form fieldset').hide();
      $('.dataset-edit-form fieldset#'+sectionToShowId).show();
      $('.dataset-edit-nav li a').removeClass('active');
      $('.dataset-edit-nav li a[href=#section-'+sectionToShowId+']').addClass('active');
      window.location.hash = 'section-'+sectionToShowId;
    }

    // Set up initial form state
    // Prefix="#section-"
    var initialSection = window.location.hash.slice(9) || 'basic-information';
    showSection(initialSection);
    
    // Adjust form state on click
    $('.dataset-edit-nav li a').live('click', function(e) {
      var $el = $(e.target);
      // Prefix="#section-"
      var showMe = $el.attr('href').slice(9);
      showSection(showMe);
      return false;
    });  
  };

  return my;
}(jQuery, CKAN.Utils || {});


CKAN.View.DatasetEditForm = Backbone.View.extend({
  initialize: function() {
    var resources = this.model.get('resources');
    var $form = this.el;

    var changesMade = function() {
      var boundToUnload = false;
      return function() {
        if (!boundToUnload) {
          CKAN.Utils.flashMessage(CKAN.Strings.youHaveUnsavedChanges,'notice');
          boundToUnload = true;
          window.onbeforeunload = function () { 
            return CKAN.Strings.youHaveUnsavedChanges; 
          };
        }
      }
    }();

    $form.find('input').live('change', function(e) {
      $target = $(e.target);
      // Entering text in the 'add' box does not represent a change
      if ($target.closest('.resource-add').length==0) {
        changesMade();
      }
    });
    resources.bind('add', changesMade);
    resources.bind('remove', changesMade);

    $form.submit(function() {
      // Don't stop us leaving
      window.onbeforeunload = null;
    });

    // Table for editing resources
    var $el = this.el.find('.js-resource-editor');
    this.resourceList=new CKAN.View.ResourceEditList({
      collection: resources,
      el: $el
    });

    // Tabbed view for adding resources
    var $el = this.el.find('.resource-add');
    this.addView=new CKAN.View.ResourceAddTabs({
      collection: resources,
      el: $el
    });

    this.addView.render();
    this.resourceList.render();
  },
});


CKAN.View.ResourceEditList = Backbone.View.extend({
  initialize: function() {
    _.bindAll(this, 'addResource', 'removeResource');
    this.collection.bind('add', this.addResource);
    this.collection.bind('remove', this.removeResource);
    this.collection.each(this.addResource);
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

  addResource: function(resource) {
    var position = this.nextIndex();
    // Create a row from the template
    var $tr = $('<tr />');
    $tr.html($.tmpl(
      CKAN.Templates.resourceEntry, 
      { resource: resource.toTemplateJSON(),
        num: position
      }
    ));
    $tr.find('.js-resource-edit-expanded').hide();
    this.el.append($tr);
    resource.view_tr = $tr;

    // == Inner Function: Toggle the expanded options set == //
    var toggleOpen = function(triggerEvent) {
      if (triggerEvent) triggerEvent.preventDefault();
      var animTime = 350;
      var expandedTable = $tr.find('.js-resource-edit-expanded');
      var finalHeight = expandedTable.height();
      var icon = 'closed';

      if (expandedTable.is(':visible')) {
        expandedTable.animate(
            {height:0},
            animTime,
            function() { 
              expandedTable.height(finalHeight);
              expandedTable.hide(); 
            }
        );
      }
      else {
        expandedTable.show();
        expandedTable.height(0);
        // Transition to its true height
        expandedTable.animate({height:finalHeight}, animTime);
        $tr.find('.js-resource-edit-name').focus();
        icon = 'open';
      }
      $tr.find('.js-resource-edit-toggle').css("background-image", "url('/images/icons/arrow-"+icon+".gif')");
    };

    // == Inner Function: Delete the row == //
    var collection = this.collection;
    var deleteResource = function(triggerEvent) {
      if (triggerEvent) triggerEvent.preventDefault();
      confirmMessage = CKAN.Strings.deleteThisResourceQuestion;
      resourceName = resource.attributes.name || CKAN.Strings.noNameBrackets;
      confirmMessage = confirmMessage.replace('%name%', resourceName);
      if (confirm(confirmMessage)) {
        collection.remove(resource);
      }
    };

    // == Inner Functions: Update the name as you type == //
    var setName = function(newName) { 
      $link = $tr.find('.js-resource-edit-toggle');
      newName = newName || ('<em>'+CKAN.Strings.noNameBrackets+'</em>');
      // Need to structurally modify the DOM to force a re-render of text
      $link.html('<ema>'+newName+'</span>');
    };
    var nameBoxChanged = function(e) {
      setName($(e.target).val());
    }

    // Trigger animation
    if (resource.isNew()) {
      toggleOpen();
    }

    var nameBox = $tr.find('input.js-resource-edit-name');
    CKAN.Utils.bindInputChanges(nameBox,nameBoxChanged);

    $tr.find('.js-resource-edit-toggle').click(toggleOpen);
    $tr.find('.js-resource-edit-delete').click(deleteResource);
    // Initialise name
    setName(resource.attributes.name);
  },

  removeResource: function(resource) {
    if (resource.view_tr) {
      resource.view_tr.remove();
      delete resource.view_tr;
    }
  },
});


CKAN.View.ResourceAddTabs = Backbone.View.extend({
  initialize: function() {
    _.bindAll(this, 'render', 'addNewResource', 'reset');
  },

  render: function() {
  },

  events: {
    'click button': 'clickButton',
    'click input[name=reset]': 'reset'
  },

  reset: function() {
    this.el.find('button').removeClass('depressed');
    if (this.subView != null) {
      this.subView.remove();
      this.subView = null;
    }
    return false;
  },

  clickButton: function(e) {
    e.preventDefault();
    var $target = $(e.target);
    
    if ($target.is('.depressed')) {
      this.reset();
    } 
    else {
      this.reset();
      $target.addClass('depressed');

      var $subPane = $('<div />').addClass('subpane');
      this.el.append($subPane);

      var tempResource = new CKAN.Model.Resource({});

      tempResource.bind('change', this.addNewResource);
      // Open sub-pane
      if ($target.is('.js-upload-file')) {
        this.subView = new CKAN.View.ResourceUpload({
          el: $subPane,
          model: tempResource,
          // TODO: horrible reverse depedency ...
          client: CKAN.UI.workspace.client
        });
      }
      else if ($target.is('.js-link-file') || $target.is('.js-link-api')) {
        this.subView = new CKAN.View.ResourceAddLink({
          el: $subPane,
          model: tempResource,
          mode: ($target.is('.js-link-file'))? 'file' : 'api',
          // TODO: horrible reverse depedency ...
          client: CKAN.UI.workspace.client
        });
      }
      this.subView.render();
    }
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


(function ($) {
  var my = {};
  my.jsonpdataproxyUrl = 'http://jsonpdataproxy.appspot.com/';

  my.setupDataPreview = function(dataset) {
    var dialogId = 'ckanext-datapreview-dialog';
    // initialize the tableviewer system
    DATAEXPLORER.TABLEVIEW.initialize(dialogId);
    my.createPreviewButtons(dataset, $('.resources'));
  };

  // Public: Creates the base UI for the plugin.
  //
  // Also requests the package from the api to see if there is any chart
  // data stored and updates the preview icons accordingly.
  //
  // dataset: Dataset model for the dataset on this page.
  // resourceElements - The resources table wrapped in jQuery.
  //
  // Returns nothing.
  my.createPreviewButtons = function(dataset, resourceElements) {
    // rather pointless, but w/o assignment dataset not available in loop below (??!)
    var currentDataset = dataset;
    resourceElements.find('tr td:last-child').each(function(idx, element) {
      var element = $(element);
      var resource = currentDataset.get('resources').models[idx];
      var resourceData = resource.toJSON();
      resourceData.formatNormalized = my.normalizeFormat(resourceData.format);

      // do not create previews for some items
      var _tformat = resourceData.format.toLowerCase();
      if (
        _tformat.indexOf('zip') != -1
        ||
        _tformat.indexOf('tgz') != -1
        ||
        _tformat.indexOf('targz') != -1
        ||
        _tformat.indexOf('gzip') != -1
        ||
        _tformat.indexOf('gz:') != -1
        ||
        _tformat.indexOf('word') != -1
        ||
        _tformat.indexOf('pdf') != -1
        ||
        _tformat === 'other'
        )
      {
        return;
      }

      var _previewSpan = $('<a />', {
        text: 'Preview',
        href: resourceData.url,
        click: function(e) {
          e.preventDefault();
          my.loadPreviewDialog(e.target);
        },
        'class': 'resource-preview-button'
      }).data('preview', resourceData).appendTo(element);

      var chartString, charts = {};

      if (resource) {
        chartString = resource[my.resourceChartKey];
        if (chartString) {
          try {
            charts = $.parseJSON(chartString);

            // If parsing succeeds add a class to the preview button.
            _previewSpan.addClass('resource-preview-chart');
          } catch (e) {}
        }
      }
    });
  };

  // **Public: Loads a data preview dialog for a preview button.**
  //
  // Fetches the preview data object from the link provided and loads the
  // parsed data from the webstore displaying it in the most appropriate
  // manner.
  //
  // link - Preview button.
  //
  // Returns nothing.
  my.loadPreviewDialog = function(link) {
    var preview  = $(link).data('preview');
    preview.url  = my.normalizeUrl(link.href);

    $(link).addClass('resource-preview-loading').text('Loading');

    // 4 situations
    // a) have a webstore_url
    // b) csv or xls (but not webstore)
    // c) can be treated as plain text
    // d) none of the above but worth iframing (assumption is
    // that if we got here (i.e. preview shown) worth doing
    // something ...)
    if (preview.formatNormalized === '') {
      var tmp = preview.url.split('/');
      tmp = tmp[tmp.length - 1];
      tmp = tmp.split('?'); // query strings
      tmp = tmp[0];
      var ext = tmp.split('.');
      if (ext.length > 1) {
        preview.formatNormalized = ext[ext.length-1];
      }
    }

    if (preview.webstore_url) {
      var _url = preview.webstore_url + '.jsontuples?_limit=500';
      my.getResourceDataDirect(_url, function(data) {
        DATAEXPLORER.TABLEVIEW.showData(data);
        DATAEXPLORER.TABLEVIEW.$dialog.dialog('open');
      });
    }
    else if (preview.formatNormalized in {'csv': '', 'xls': ''}) {
      var _url = my.jsonpdataproxyUrl + '?url=' + preview.url + '&type=' + preview.formatNormalized;
      my.getResourceDataDirect(_url, function(data) {
        DATAEXPLORER.TABLEVIEW.showData(data);
        DATAEXPLORER.TABLEVIEW.$dialog.dialog('open');
      });
    }
    else if (preview.formatNormalized in {
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
      var _url = my.jsonpdataproxyUrl + '?type=csv&url=' + preview.url;
      my.getResourceDataDirect(_url, function(data) {
        my.showPlainTextData(data);
        DATAEXPLORER.TABLEVIEW.$dialog.dialog('open');
      });
    }
    else {
      // HACK: but should work
      // we displays a fullscreen dialog with the url in an iframe.
      // HACK: we borrow dialog from DATAEXPLORER.TABLEVIEW
      var $dialog = DATAEXPLORER.TABLEVIEW.$dialog;
      $dialog.empty();
      $dialog.dialog('option', 'title', 'Preview: ' + preview.url);
      var el = $('<iframe></iframe>');
      el.attr('src', preview.url);
      el.attr('width', '100%');
      el.attr('height', '100%');
      $dialog.append(el).dialog('open');;
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
    // HACK: have to reach into DATAEXPLORER.TABLEVIEW dialog  a lot ...
    DATAEXPLORER.TABLEVIEW.setupFullscreenDialog();

    if(data.error) {
      DATAEXPLORER.TABLEVIEW.showError(data.error);
    } else {
      var content = $('<pre></pre>');
      for (var i=0; i<data.data.length; i++) {
        var row = data.data[i].join(',') + '\n';
        content.append(my.escapeHTML(row));
      }
      DATAEXPLORER.TABLEVIEW.$dialog.dialog(DATAEXPLORER.TABLEVIEW.dialogOptions);
      DATAEXPLORER.TABLEVIEW.$dialog.append(content);
    }
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
}(jQuery));

