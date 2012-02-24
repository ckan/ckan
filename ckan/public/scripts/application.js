(function ($) {
  $(document).ready(function () {
    CKAN.Utils.setupUserAutocomplete($('input.autocomplete-user'));
    CKAN.Utils.setupPublisherUserAutocomplete($('input.autocomplete-publisher-user'));
    CKAN.Utils.setupGroupAutocomplete($('input.autocomplete-group'));
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

    // Buttons with href-action should navigate when clicked
    $('input.href-action').click(function(e) {
      e.preventDefault();
      window.location = ($(e.target).attr('action'));
    });

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
      $('.js-scroll-resources').click(function() {
        var header = $('#dataset-resources > h3:first-child');
        $("html,body").animate({ scrollTop: header.offset().top }, 500);
      });
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

    var isDatasetEdit = $('body.package.edit').length > 0;
    if (isDatasetEdit) {
      CKAN.Utils.warnOnFormChanges($('form#dataset-edit'));
      CKAN.Utils.setupUrlEditor('package',readOnly=true);

      // Set up hashtag nagivigation
      CKAN.Utils.setupDatasetEditNavigation();

      // Set up dataset delete button
      CKAN.Utils.setupDatasetDeleteButton();
    }
    var isDatasetResourceEdit = $('body.package.editresources').length > 0;
    if (isDatasetNew || isDatasetResourceEdit) {
      // Selectively enable the upload button
      var storageEnabled = $.inArray('storage',CKAN.plugins)>=0;
      if (storageEnabled) {
        $('li.js-upload-file').show();
      }
      // Backbone model/view
      var _dataset = new CKAN.Model.Dataset(preload_dataset);
      var $el=$('form#dataset-edit');
      var view=new CKAN.View.ResourceEditor({
        collection: _dataset.get('resources'),
        el: $el
      });
      view.render();

      $( ".drag-drop-list" ).sortable({
        distance: 10
      });
      $( ".drag-drop-list" ).disableSelection();
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
  };

  my.setupDatasetDeleteButton = function() {
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
  };

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

  my.setupPublisherUserAutocomplete = function(elements) {
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
      },
       select: function(event, ui) {
        var input_box = $(this);
        input_box.val('');
        var parent_dd = input_box.parent('dd');
        var old_name = input_box.attr('name');
        var field_name_regex = /^(\S+)__(\d+)__(\S+)$/;
        var split = old_name.match(field_name_regex);

        var new_name = split[1] + '__' + (parseInt(split[2]) + 1) + '__' + split[3]
        input_box.attr('name', new_name)
        input_box.attr('id', new_name)

        var capacity = $("input:radio[name=add-user-capacity]:checked").val();
        parent_dd.before(
          '<input type="hidden" name="' + old_name + '" value="' + ui.item.value + '">' +
          '<input type="hidden" name="' + old_name.replace('__name','__capacity') + '" value="' + capacity + '">' +
          '<dd>' + ui.item.label + '</dd>'
        );

        return false; // to cancel the event ;)
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

  my.setupGroupAutocomplete = function(elements) {
    elements.autocomplete({
      minLength: 2,
      source: function(request, callback) {
        var url = CKAN.SITE_URL + '/api/2/util/group/autocomplete?q=' + request.term;
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
    var paragraphs = notes.find('#notes-extract > *');
    if (paragraphs.length==0) {
      notes.hide();
    }
    else if (paragraphs.length > 1) {
      var remainder = notes.find('#notes-remainder');
      $.each(paragraphs,function(i,para) {
        if (i > 0) remainder.append($(para).remove());
      });
      notes.find('#notes-toggle').show();
      notes.find('#notes-toggle button').click(
        function(event){
          notes.find('#notes-toggle button').toggle();
          if ($(event.target).hasClass('more'))
            remainder.slideDown();
          else
            remainder.slideUp();
          return false;
        }
      );
    }
  };

  my.warnOnFormChanges = function() {
    var boundToUnload = false;
    return function($form) {
      var flashWarning = function() {
        if (boundToUnload) return;
        boundToUnload = true;
        // Don't show a flash message
        //var parentDiv = $('<div />').addClass('flash-messages');
        //var messageDiv = $('<div />').html(CKAN.Strings.youHaveUnsavedChanges).addClass('notice').hide();
        //parentDiv.append(messageDiv);
        //$('#unsaved-warning').append(parentDiv);
        //messageDiv.show(200);
        // Bind to the window departure event
        window.onbeforeunload = function () {
          return CKAN.Strings.youHaveUnsavedChanges;
        };
      }
      // Hook form modifications to flashWarning
      $form.find('input,select').live('change', function(e) {
        $target = $(e.target);
        // Entering text in the 'add' box does not represent a change
        if ($target.closest('.resource-add').length==0) {
          flashWarning();
        }
      });
      // Don't stop us leaving
      $form.submit(function() {
        window.onbeforeunload = null;
      });
      // Calling functions might hook to flashWarning
      return flashWarning;
    };
  }();

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


CKAN.View.ResourceEditor = Backbone.View.extend({
  initialize: function() {
    // Init bindings
    _.bindAll(this, 'resourceAdded', 'resourceRemoved', 'sortStop', 'openFirstPanel', 'closePanel', 'openAddPanel');
    this.collection.bind('add', this.resourceAdded);
    this.collection.bind('remove', this.resourceRemoved);
    this.collection.each(this.resourceAdded);
    this.el.find('.resource-list-edit').bind("sortstop", this.sortStop);

    // Delete the barebones editor. We will populate our own form.
    this.el.find('.js-resource-edit-barebones').remove();

    // Warn on form changes
    var flashWarning = CKAN.Utils.warnOnFormChanges(this.el);
    this.collection.bind('add', flashWarning);
    this.collection.bind('remove', flashWarning);

    // Trigger the Add Resource pane
    this.el.find('.js-resource-add').click(this.openAddPanel);

    // Tabbed view for adding resources
    var $resourceAdd = this.el.find('.resource-add');
    this.addView=new CKAN.View.ResourceAddTabs({
      collection: this.collection,
      el: $resourceAdd
    });

    // Close details button
    this.el.find('.resource-panel-close').click(this.closePanel);

    this.openFirstPanel();
  },
  /*
   * Called when the page loads or the current resource is deleted. 
   * Reset page state to the first available edit panel.
   */
  openFirstPanel: function() {
    if (this.collection.length>0) {
      this.collection.at(0).view.openMyPanel();
    }
    else {
      this.openAddPanel();
    }
  },
  /*
   * Open the 'Add New Resource' special-case panel on the right.
   */
  openAddPanel: function(e) {
    if (e) e.preventDefault();
    this.el.find('.resource-list li').removeClass('active');
    this.el.find('.resource-list-add li').addClass('active');
    this.el.find('.resource-details').hide();
    this.el.find('.resource-details.resource-add').show();
    this.el.find('.resource-panel').show();
  },
  /*
   * Close the panel on the right.
   */
  closePanel: function(e) {
    if (e) e.preventDefault();
    this.el.find('.resource-list li').removeClass('active');
    this.el.find('.resource-panel').hide();
  },
  /* 
   * Update the resource__N__field names to match 
   * new sort order.
  */
  sortStop: function(e,ui) {
    this.collection.each(function(resource) {
      // Ask the DOM for the new sort order
      var index = resource.view.li.index();
      // Update the form element names
      var table = resource.view.table;
      $.each(table.find('input,textarea,select'), function(input_index, input) {
        var name = $(input).attr('name');
        name = name.replace(/(resources__)\d+(.*)/, '$1'+index+'$2')
        $(input).attr('name',name);
      });
    });
  },
  /* 
   * Calculate id of the next resource to create 
   */
  nextIndex: function() {
    var maxId=-1;
    var root = this.el.find('.resource-panel');
    root.find('input').each(function(idx,input) {
      var splitName=$(input).attr('name').split('__');
      if (splitName.length>1) {
        var myId = parseInt(splitName[1])
        maxId = Math.max(myId, maxId);
      }
    });
    return maxId+1;
  },
  /* 
   * Create DOM elements for new resource. 
   */
  resourceAdded: function(resource) {
    var self = this;
    resource.view = new CKAN.View.Resource({
      position: this.nextIndex(),
      model: resource,
      callback_deleteMe: function() { self.collection.remove(resource); }
    });
    this.el.find('.resource-list-edit').append(resource.view.li);
    this.el.find('.resource-panel').append(resource.view.table);
    if (resource.isNew()) {
      resource.view.openMyPanel();
    }
  },
  /* 
   * Destroy DOM elements for deleted resource.
   */
  resourceRemoved: function(resource) {
    resource.view.removeFromDom();
    delete resource.view;
    this.openFirstPanel();
  },
});


/*
 * Backbone view of a resource.
 * Creates two DOM elements: The draggable li (left) and the tabular editor (right).
 */
CKAN.View.Resource = Backbone.View.extend({
  initialize: function() {
    _.bindAll(this,'updateName','updateIcon','name','askToDelete','openMyPanel');
    // Generate DOM elements
    var resource_object = { 
        resource: this.model.toTemplateJSON(),
        num: this.options.position,
        resource_icon: '/images/icons/page_white.png',
        resourceTypeOptions: [
          ['file', 'Data File']
          , ['api', 'API']
          , ['image', 'Image']
          , ['metadata', 'Metadata']
          , ['documentation', 'Documentation']
          , ['code', 'Code']
          , ['example', 'Example']
        ]
    };
    this.li = $($.tmpl(CKAN.Templates.resourceEntry, resource_object));
    this.table = $($.tmpl(CKAN.Templates.resourceDetails, resource_object));

    // Hook to changes in name
    this.nameBox = this.table.find('input.js-resource-edit-name');
    this.descriptionBox = this.table.find('textarea.js-resource-edit-description');
    CKAN.Utils.bindInputChanges(this.nameBox,this.updateName);
    CKAN.Utils.bindInputChanges(this.descriptionBox,this.updateName);
    // Hook to changes in format
    this.formatBox = this.table.find('input.js-resource-edit-format');
    CKAN.Utils.bindInputChanges(this.formatBox,this.updateIcon);
    // Hook to delete button
    this.table.find('.js-resource-edit-delete').click(this.askToDelete);
    // Hook to open panel link
    this.li.find('.resource-open-my-panel').click(this.openMyPanel);

    // Set initial state
    this.updateName();
    this.updateIcon();
  },
  /* 
   * Work out what I should be called. Rough-match 
   * of helpers.py:resource_display_name. 
   */
  name: function() {
    var name = this.nameBox.val();
    if (!name) {
      name = this.descriptionBox.val();
      if (!name) {
        if (this.model.isNew()) {
          name = '<em>[new resource]</em>';
        }
        else {
          name = '[no name] ' + this.model.id;
        }
      }
    }
    if (name.length>45) {
      name = name.substring(0,45)+'...';
    }
    return name;
  },
  /* 
   * Called when the user types to update the name in 
   * my <li> to match the <input> values. 
   */
  updateName: function() {
    // Need to structurally modify the DOM to force a re-render of text
    var $link = this.li.find('.js-resource-edit-name');
    $link.html('<span>'+this.name()+'</span>');
  },
  /* 
   * Called when the user types to update the icon <img> 
   * tags. Uses server API to select icon.
   */
  updateIcon: function() {
    var self = this;
    // AJAX to server API
    $.getJSON('/api/2/util/format_icon?format='+this.formatBox.val(), function(data) {
      if (data.icon) {
        self.li.find('.js-resource-icon').attr('src',data.icon);
        self.table.find('.js-resource-icon').attr('src',data.icon);
      }
    });
  },
  /*
   * Closes all other panels on the right and opens my editor panel.
   */
  openMyPanel: function(e) {
    if (e) e.preventDefault();
    // Close all tables
    var panel = this.table.parents('.resource-panel');
    panel.find('.resource-details').hide();
    this.li.parents('fieldset#resources').find('li').removeClass('active');
    panel.show();
    this.table.show();
    this.table.find('.js-resource-edit-name').focus();
    this.li.addClass('active');
  },
  /* 
   * Called when my delete button is clicked. Calls back to the parent
   * resource editor.
   */
  askToDelete: function(e) {
    e.preventDefault();
    var confirmMessage = CKAN.Strings.deleteThisResourceQuestion.replace('%name%', this.name());
    if (confirm(confirmMessage)) {
      this.options.callback_deleteMe();
    }
  },
  /* 
   * Called when my model is destroyed. Remove me from the page.
   */
  removeFromDom: function() {
    this.li.remove();
    this.table.remove();
  }
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

