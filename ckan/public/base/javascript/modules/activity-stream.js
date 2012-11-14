/* Activity stream
 * Handle the loading more of activity items within actiivity streams
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
		},

		_onBuildLoadMore: function() {
			var options = this.options;
			if (options.more) {
				$('.load-more', this.el).on('click', 'a', this._onLoadMoreClick);
				options.offset = $('.item', this.el).length;
			}
		},

		_onLoadMoreClick: function (event) {
			event.preventDefault();
			var options = this.options;
			if (!options.loading) {
				options.loading = true;
				$('.load-more a', this.el).html(this.i18n('loading')).addClass('disabled');
				this.sandbox.client.call('GET', options.context+'_activity_list_html', '?id='+options.id+'&offset='+options.offset, this._onActivitiesLoaded);
			}
		},

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
