(function ($) {
  $(document).ready(function () {
    CKAN.Utils.setupUserAutocomplete($('input.autocomplete-user'));
    CKAN.Utils.setupAuthzGroupAutocomplete($('input.autocomplete-authzgroup'));
    CKAN.Utils.setupPackageAutocomplete($('input.autocomplete-dataset'));
    CKAN.Utils.setupTagAutocomplete($('input.autocomplete-tag'));
    CKAN.Utils.setupFormatAutocomplete($('input.autocomplete-format'));
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
            valid_msg.html('<span style="font-weight: bold; color: #0c0">This dataset name is available!</span>');
          } else {
            valid_msg.html('<span style="font-weight: bold; color: #c00">This dataset name is already used, please use a different name</span>');
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

