
<script type="text/javascript">
//<![CDATA[
(function($){
    $.fn.ajaxCreateSlug = function(name, url) {
        var title = this;
        var updater = {
            init: function(title, name) {
                // Add a new element where the validity of the package name can be displayed
                this.name_field = name;
                this.title_field = title;
                this.name_field.parent().append('<div id="package_name_valid_msg"></div>');
                this.title_field.blur(this.title_change_handler())
                this.title_field.keyup(this.title_change_handler())
                this.name_field.keyup(this.name_change_handler());
                this.name_field.blur(this.name_blur_handler());
                this.url = url;
            },
            title_change_handler: function() {
                var self = this;
                return function() {
                    if (!self.name_changed && self.title_field.val().replace(/^\s+|\s+$/g, '')) {
                        self.update(self.title_field.val(), function(data) {self.name_field.val(data.name)});
                    }
                }
            },
            name_blur_handler: function() {
                var self = this;
                return function() {
                    // Reset if the name is emptied
                    if (!self.name_field.val().replace(/^\s+|\s+$/g, '')){
                        self.name_changed = false;
                        $('#package_name_valid_msg').html('');
                    } else {
                        self.update(self.name_field.val(), function(data) {
                            self.name_field.val(data.name)
                        });
                    }
                };
            },
            name_change_handler: function() {
                var self = this;
                return function() {
                    // Reset if the name is emptied
                    if (!self.name_field.val().replace(/^\s+|\s+$/g, '')){
                        self.name_changed = false;
                        $('#package_name_valid_msg').html('');
                    } else {
                        self.name_changed = true;
                        self.update(self.name_field.val(), function(data) {
                            if (self.name_field.val().length >= data.name) {
                                self.name_field.val(data.name);
                            }
                        });
                    }
                };
            },
            // Keep a variable where we can store whether the name field has been
            // directly modified by the user or not. If it has, we should no longer
            // fetch updates.
            name_changed: false,
            // Create a function for fetching the value and updating the result
            perform_update: function(value, on_success){
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
                        var valid_msg = $('#package_name_valid_msg');
                        if (data.valid) {
                            valid_msg.html('<span style="font-weight: bold; color: #0c0">This package name is available!</span>');
                        } else {
                            valid_msg.html('<span style="font-weight: bold; color: #c00">This package name is already used, please use a different name</span>');
                        }
                    }
                });
            },
            // We only want to perform the update if there hasn't been a change for say 200ms
            timer: null,
            update: function(value, on_success) {
                var self = this;
                if (this.timer) {
                    clearTimeout(this.timer)
                };
                this.timer = setTimeout(function () {
                    self.perform_update(value, on_success)
                }, 200);
            }
        }
        updater.init(title, $(name), url);
        return title;
    };
})( jQuery );
$(document).ready(function() {
    $('#title').ajaxCreateSlug('#name', '/api/2/util/package/create_slug');
});

$(document).ready(function () {
    if (!$('#preview').length) {
        $("#title").focus();
    }
});
//]]>
</script>
