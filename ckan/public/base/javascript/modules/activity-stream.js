/* Activity stream
 * Handle the pagination for activity list
 *
 * Options
 * - page: current page number
 */	
this.ckan.module('activity-stream', function($) {
	return {
		
		/* Initialises the module setting up elements and event listeners.
		 *
		 * Returns nothing.
		 */
		initialize: function () {
			$('#activity_types_filter_select').on(
				'change',
				this._onChangeActivityType
			);
		},

		
		/* Filter using the selected 
		 *   activity type
		 *
		 * Returns nothing
		 */
		_onChangeActivityType: function (event) {
			// event.preventDefault();
			url = $("#activity_types_filter_select option:selected" ).data('url');
			window.location = url;
		},

	};
});
