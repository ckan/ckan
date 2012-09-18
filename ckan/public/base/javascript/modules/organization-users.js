/*
 * Module for the organizations users table
 */
this.ckan.module('organization-users', function ($, _) {
	return {

		options: {
			index: 0,
			users: '',
			i18n: {
				addTitle: _('Add user')
			}
		},

		initialize: function () {
			// ok
			this.options.users = this.options.users.split('~~');
			// convert all the keep labels into buttons
			$('.organizations-remove', this.el).each(this.initializeRemove);
			// ok checkbox change toggle the disabled state for display
			this.el.on('change', '.organizations-remove :checkbox', function() {
				var row = $(this).parents('tr');
				row.toggleClass('disabled');
				$('input[type=radio]', row).prop('disabled', !$(this).prop('checked'));
				$('.btn', row).toggleClass('btn-info');
			});
			// now init the add
			this.initializeAdd();
		},

		// Initializes the remove button on each table row of the user table
		initializeRemove: function() {
			$(this).addClass('btn btn-danger pull-right checkbox');
			$('span', this).html('').addClass('icon-remove');
		},

		// Handles the logic of adding users to the table
		initializeAdd: function() {
			var templateForm = $('#organizations-add-form');
			// add the  button to the page actions
			var add = $('<li><a href="javascript:;" class="btn btn-success" data-toggle="button"><span class="icon-plus-sign"></span> ' + this.i18n('addTitle') + '</a></li>')
				.insertAfter('#organizations-back');
			$('a', add)
				// this is needed for in jQuery event callbacks
				.data('me', this)
				// ok create a popover from the template
				.popover({
					title: this.i18n('addTitle'),
					content: templateForm.html(),
					placement: 'left'
				})
				// we have to do some of this logic on click because the
				// popover only populates the html on first click...
				.on('click', this._handlePopoverShow);
			// ok let's do a bit of dom tidying
			$('.organizations-add', this.el).add(templateForm).remove();
		},

		// This fired whenever the popover is shown
		_handlePopoverShow: function() {
			var $this = $(this);
			var me = $this.data('me');
			// get the popover tooltip
			var tip = $this.data('popover').tip();
			// now get the popover input
			var input = $('input', tip);

			// has this been inited before?
			if (!input.data('inited')) {
				// make the input a autocomplete dropdown
				var Module = ckan.module.registry['autocomplete'];
				ckan.module.createInstance(Module, input[0]);
				// add the org class for styling form
				tip.addClass('organization-popover-add');
				// add the listener to the button
				$('.btn', tip)
					.data('me', me)
					.data('btn', $this)
					.on('click', me._handleAddUserToTable);
				// tell everyone that this has been inited now
				input.data('inited', true);
			}

		},

		// This actually adds a given username to the users table
		_handleAddUserToTable: function() {
			var me = $(this).data('me');
			// what's the username they want to add?
			var username = $('input', $(this).parent()).val();
			// ok validate the username they want to add
			if (me._validateUsername(username)) {
				// setup the template
				var templateRow = $('#organizations-add-row')
					.html()
					.replace(/\[username\]/g, username)
					.replace(/\[index\]/g, me.options.index);
				// ok add the row to the table
				var added = $(templateRow).appendTo($('table tbody', me.el)).hide().fadeIn();
				// and init the remove button
				$('.organizations-remove', added).each(me.initializeRemove);
				// add one to the index
				me.options.index++;
				// add the username to the checklist
				me.options.users.push(username);
				// now hide the popover
				$(this).data('btn').trigger('click');
			}
		},

		// Validates a given username
		_validateUsername: function(username) {
			// is there a username?
			var username = $.trim(username);
			if (!username) {
				return false;
			}
			// is it a username in the table already?
			for (var i = 0; i < this.options.users.length; i++) {
				if (this.options.users[i] == username) {
					return false;
				}
			}
			// everything is fine
			return true;
		}

	}
});
