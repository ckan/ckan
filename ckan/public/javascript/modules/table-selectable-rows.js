/* Table Selectable Rows
 * Put's a select box in the <thead> of a <table> and makes all rows
 * selectable.
 *
 * Examples
 *
 *   <table data-module="table-selectable-rows">...</table>
 *
 */
this.ckan.module('table-selectable-rows', function($, _) {
	return {

		// Store for jQuery object for the select all checkbox
		select_all: null,
		// Total number of checkboxes in the table (used for checking later)
		total_checkboxes: 0,
		// Store for jQuery object of all table header buttons
		buttons: null,

		/* Initialises the module setting up elements and event listeners.
		 *
		 * Returns nothing.
		 */
		initialize: function() {
			$.proxyAll(this, /_on/);
			this.total_checkboxes = $('input[type="checkbox"]', this.el).length;
			this.select_all = $('<input type="checkbox">')
				.data('select-all', true)
				.appendTo($('thead th:first-child', this.el));
			this.el.on('change', 'input[type="checkbox"]', this._onHandleCheckboxToggle);
			this.buttons = $('th.actions .btn', this.el).addClass('disabled').prop('disabled', true);
		},

		/* Gets called whenever a user changes the :checked state on a checkbox
		 * within the table
		 *
		 * $e - jQuery event object
		 *
		 * Returns nothing.
		 */
		_onHandleCheckboxToggle: function($e) {
			var checkbox = $($e.target);
			if (checkbox.data('select-all')) {
				this.handleSelectAll(checkbox, checkbox.is(':checked'));
			} else {
				this.handleSelectOne(checkbox, checkbox.is(':checked'));
			}
		},

		/* Handles the checking of all row
		 *
		 * $target - jQuery checkbox object
		 * $checked - Boolean of whether $target is checked
		 *
		 * Returns nothing.
		 */
		handleSelectAll: function($target, $checked) {
			$('input[type="checkbox"]', this.el).prop('checked', $checked);
			if ($checked) {
				$('tbody tr', this.el).addClass('table-selected');
				this.buttons.removeClass('disabled').prop('disabled', false);
			} else {
				$('tbody tr', this.el).removeClass('table-selected');
				this.buttons.addClass('disabled').prop('disabled', true);
			}
		},

		/* Handles the checking of a single row
		 *
		 * $target - jQuery checkbox object
		 * $checked - Boolean of whether $target is checked
		 *
		 * Returns nothing.
		 */
		handleSelectOne: function($target, $checked) {
			if ($checked) {
				$target.parents('tr').addClass('table-selected');
			} else {
				$target.parents('tr').removeClass('table-selected');
			}
			var checked = $('tbody input[type="checkbox"]:checked', this.el).length;
			if (checked >= this.total_checkboxes) {
				this.select_all.prop('checked', true);
			} else {
				this.select_all.prop('checked', false);
			}
			if (checked > 0) {
				this.buttons.removeClass('disabled').prop('disabled', false);
			} else {
				this.buttons.addClass('disabled').prop('disabled', true);
			}
		}

	};
});
