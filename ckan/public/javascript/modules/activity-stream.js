/* Activity stream
 * Handle the loading more of activity items within actiivity streams
 *
 * Options
 * - more: are there more items to load
 * - context: what's the context for the ajax calls
 * - id: what's the id of the context?
 * - offset: what's the current offset?
 */	
this.ckan.module('activity-stream', function($, _) {
	return {
		/* options object can be extended using data-module-* attributes */
		options : {
			more: null,
			id: null,
			context: null,
			offset: null,
			loading: false,
			i18n: {
				loading: _('Loading...')
			}
		},

		/* Initialises the module setting up elements and event listeners.
		 *
		 * Returns nothing.
		 */
		initialize: function () {
			$.proxyAll(this, /_on/);
			var options = this.options;
			options.more = (options.more == 'True');
			this._onBuildLoadMore();
			$(window).on('scroll', this._onScrollIntoView);
			this._onScrollIntoView();
		},

		/* Function that tells if el is within the window viewpost
		 *
		 * Returns boolean
		 */
		elementInViewport: function(el) {
			var top = el.offsetTop;
			var left = el.offsetLeft;
			var width = el.offsetWidth;
			var height = el.offsetHeight;
			while(el.offsetParent) {
				el = el.offsetParent;
				top += el.offsetTop;
				left += el.offsetLeft;
			}
			return (
				top < (window.pageYOffset + window.innerHeight) &&
				left < (window.pageXOffset + window.innerWidth) &&
				(top + height) > window.pageYOffset &&
				(left + width) > window.pageXOffset
			);
		},

		/* Whenever the window scrolls check if the load more button
		 * exists, if it's in the view and we're not already loading.
		 * If all conditions are satisfied... fire a click event on
		 * the load more button.
		 *
		 * Returns nothing
		 */
		_onScrollIntoView: function() {
			var el = $('.load-more a', this.el);
			if (el.length == 1) {
				var in_viewport = this.elementInViewport(el[0]);
				if (in_viewport && !this.options.loading) {
					el.trigger('click');
				}	
			}
		},

		/* If we are able to load more... then attach the ajax request
		 * to the load more button.
		 *
		 * Returns nothing
		 */
		_onBuildLoadMore: function() {
			var options = this.options;
			if (options.more) {
				$('.load-more', this.el).on('click', 'a', this._onLoadMoreClick);
				options.offset = $('.item', this.el).length;
			}
		},

		/* Fires when someone clicks the load more button
		 * ... and if not loading then make the API call to load
		 * more activities
		 *
		 * Returns nothing
		 */
		_onLoadMoreClick: function (event) {
			event.preventDefault();
			var options = this.options;
			if (!options.loading) {
				options.loading = true;
				$('.load-more a', this.el).html(this.i18n('loading')).addClass('disabled');
				this.sandbox.client.call('GET', options.context+'_activity_list_html', '?id='+options.id+'&offset='+options.offset, this._onActivitiesLoaded);
			}
		},

		/* Callback for after the API call
		 *
		 * Returns nothing
		 */
		_onActivitiesLoaded: function(json) {
			var options = this.options;
			var result = $(json.result);
			options.more = ( result.data('module-more') == 'True' );
			options.offset += 30;
			$('.load-less', result).remove();
			$('.load-more', this.el).remove();
			$('li', result).appendTo(this.el);
			this._onBuildLoadMore();
			options.loading = false;
		}

	};
});
