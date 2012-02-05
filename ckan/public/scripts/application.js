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
      endpoint: CKAN.SITE_URL + '/'
    };
    var client = new CKAN.Client(config);
    // serious hack to deal with hacky code in ckanjs
    CKAN.UI.workspace = {
      client: client
    };

    var isFrontPage = $('body.index.home').length > 0;
    if (isFrontPage) {
      CKAN.Utils.setupWelcomeBanner($('.js-welcome-banner'));
    }

    var isGroupView = $('body.group.read').length > 0;
    if (isGroupView) {
      // Show extract of notes field
      CKAN.Utils.setupNotesExtract();
    }

    var isDatasetView = $('body.package.read').length > 0;
    if (isDatasetView) {
      // Show extract of notes field
      CKAN.Utils.setupNotesExtract();
    }

    var isResourceView = $('body.package.resource_read').length > 0;
    if (isResourceView) {
      CKANEXT.DATAPREVIEW.loadPreviewDialog(preload_resource);
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

      // Set up dataset delete button
      var select = $('select.dataset-delete');
      select.attr('disabled','disabled');
      select.css({opacity: 0.3});
      $('button.dataset-delete').click(function(e) {
        select.removeAttr('disabled');
        select.fadeTo('fast',1.0);
        $(e.target).css({opacity:0});
        $(e.target).attr('disabled','disabled');
        return false;
      });
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

  // Animate the appearance of an element by expanding its height
  my.animateHeight = function(element, animTime) {
    if (!animTime) animTime = 350;
    element.show();
    var finalHeight = element.height();
    element.height(0);
    element.animate({height:finalHeight}, animTime);
  }

  my.bindInputChanges = function(input, callback) {
    input.keyup(callback);
    input.keydown(callback);
    input.keypress(callback);
    input.change(callback);
  };

  my.setupWelcomeBanner = function(banner) {

    var cookieName = 'ckan_killtopbar';
    var isKilled = ($.cookie(cookieName)!=null);
    if (!isKilled) {
      banner.show();
      // Bind to the close button
      banner.find('.js-kill-button').live('click', function() {
        $.cookie(cookieName, 'true', { expires: 365 });
        banner.hide();
      });
    }
  };

  my.setupUrlEditor = function(slugType,readOnly) {
    // Page elements to hook onto
    var titleInput = $('.js-title');
    var urlText = $('.js-url-text');
    var urlSuffix = $('.js-url-suffix');
    var urlInput = $('.js-url-input');
    var validMsg = $('.js-url-is-valid');

    if (titleInput.length==0) throw "No titleInput found.";
    if (urlText.length==0) throw "No urlText found.";
    if (urlSuffix.length==0) throw "No urlSuffix found.";
    if (urlInput.length==0) throw "No urlInput found.";
    if (validMsg.length==0) throw "No validMsg found.";

    var api_url = CKAN.SITE_URL + '/api/2/util/is_slug_valid';
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
        if (timer) clearTimeout(timer);
        if (slug.length<2) {
          validMsg.html('<span style="font-weight: bold; color: #444;">'+CKAN.Strings.urlIsTooShort+'</span>');
        }
        else {
          validMsg.html('<span style="color: #777;">'+CKAN.Strings.checking+'</span>');
          timer = setTimeout(function () {
            checkSlugValid(slug);
          }, 200);
        }
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
          var _realTerm = request.term.split(',').pop().trim();
          var url = CKAN.SITE_URL + '/api/2/util/tag/autocomplete?incomplete=' + _realTerm;
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
          var terms = this.value.split(',');
          // remove the current input
          terms.pop();
          // add the selected item
          terms.push( " "+ui.item.value );
          // add placeholder to get the comma-and-space at the end
          terms.push( " " );
          this.value = terms.join( "," );
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
        var url = CKAN.SITE_URL + '/api/2/util/resource/format_autocomplete?incomplete=' + request.term;
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
        var url = CKAN.SITE_URL + '/api/2/util/user/autocomplete?q=' + request.term;
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
        var url = CKAN.SITE_URL + '/api/2/util/authorizationgroup/autocomplete?q=' + request.term;
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
        $.post(CKAN.SITE_URL + "/api/util/markdown", { q: raw_markdown },
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

  // If notes field is more than 1 paragraph, just show the
  // first paragraph with a 'Read more' link that will expand
  // the div if clicked
  my.setupNotesExtract = function() {
    var notes = $('#content div.notes');
    if(notes.find('p').length > 1){
      var extract = notes.children(':eq(0)');
      var remainder = notes.children(':gt(0)');
      notes.html($.tmpl(CKAN.Templates.notesField));
      notes.find('#notes-extract').html(extract);
      notes.find('#notes-remainder').html(remainder);
      notes.find('#notes-remainder').hide();
      notes.find('#notes-toggle a').click(function(event){
        notes.find('#notes-toggle a').toggle();
        var remainder = notes.find('#notes-remainder')
        if ($(event.target).hasClass('more')) {
          remainder.slideDown();
        }
        else {
          remainder.slideUp();
        }
        return false;
      })
    }
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
          var parentDiv = $('<div />').addClass('flash-messages');
          var messageDiv = $('<div />').html(CKAN.Strings.youHaveUnsavedChanges).addClass('notice').hide();
          parentDiv.append(messageDiv);
          $('#unsaved-warning').append(parentDiv);
          messageDiv.show(200);

          boundToUnload = true;
          window.onbeforeunload = function () { 
            return CKAN.Strings.youHaveUnsavedChanges; 
          };
        }
      }
    }();

    $form.find('input,select').live('change', function(e) {
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
        num: position,
        resourceTypeOptions: [
          ['file', 'Data File']
          , ['api', 'API']
          , ['image', 'Image']
          , ['metadata', 'Metadata']
          , ['documentation', 'Documentation']
          , ['code', 'Code']
          , ['example', 'Example']
        ]
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
  my.dialogId = 'ckanext-datapreview';
  my.$dialog = $('#' + my.dialogId);

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

    function initializeDataExplorer(dataset) {
      var dataExplorer = new recline.View.DataExplorer({
        el: my.$dialog
        , model: dataset
        , config: {
          readOnly: true
        }
      });
      // will have to refactor if this can get called multiple times
      Backbone.history.start();
    }

    // 4 situations
    // a) have a webstore_url
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
      var backend = new recline.Model.BackendWebstore({
        url: resourceData.webstore_url
      });
      recline.Model.setBackend(backend);
      var dataset = backend.getDataset();
      initializeDataExplorer(dataset);
    }
    else if (resourceData.formatNormalized in {'csv': '', 'xls': ''}) {
      var backend = new recline.Model.BackendDataProxy({
        url: resourceData.url
        , type: resourceData.formatNormalized
      });
      recline.Model.setBackend(backend);
      var dataset = backend.getDataset();
      initializeDataExplorer(dataset);
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
        title: 'Preview not available for data type: ' + resourceData.formatNormalized
        , message: ''
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
        '<div class="alert-message warning"><strong><%= title %></strong><br /><%= message %></div>'
        , error
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
}(jQuery));

