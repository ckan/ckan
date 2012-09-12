/*
 * Module for the organizations users table
 */
this.ckan.module('organization-users', function ($, _) {
	return {
		initialize: function () {
			// convert all the keep labels into buttons
			$('.orginization-remove', this.el).each(function() {
				$(this).addClass('btn btn-danger pull-right checkbox');
				$('span', this).html('').addClass('icon-remove');
			});
			// ok checkbox change toggle the disabled state for display
			this.el.on('change', '.orginization-remove :checkbox', function() {
				var row = $(this).parents('tr');
				row.toggleClass('disabled');
				$('input[type=radio]', row).prop('disabled', !$(this).prop('checked'));
				$('.btn', row).toggleClass('btn-info');
			});
		}
	}
});
