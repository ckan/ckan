/* Popover context
 * These appear when someone hovers over a context item in a activity stream to
 * give the user more context into that particular item. It also allows for
 * people to follow and unfollow quickly from within the popover
 *
 * id - The user_id of user
 * context - The type of this popover: currently supports user & package

 * url - The URL of the profile for that user
 * loading - Loading state helper
 * authed - Is the current user authed ... if so what's their user_id
 * template - Simple string-replace template for content of popover
 *
 * Examples
 *
 *   <a data-module="popover-context" data-module-context="user" data-module-id="{user_id}">A user</a>
 *
 */

// Global dictionary and render store for items
window.popover_context = {
	dict: {
		user: {},
		dataset: {},
		group: {}
	},
	render: {
		user: {},
		dataset: {},
		group: {}
	}
};

this.ckan.module('popover-context', function($) {
	return {

		/* options object can be extended using data-module-* attributes */
		options : {
			id: null,
			loading: false,
			error: false,
			authed: false,
			throbber: '<img src="{SITE_ROOT}/base/images/loading-spinner.gif">'
		},

		/* Initialises the module setting up elements and event listeners.
		 *
		 * Returns nothing.
		 */
		initialize: function() {
			if (
				this.options.id != true
				&& this.options.id != null
			) {
				$.proxyAll(this, /_on/);
				if ($('.account').hasClass('authed')) {
					this.options.authed = $('.account').data('me');
				}
				this.el.popover({
					animation: false,
					html: true,
					content: this.options.throbber.replace('{SITE_ROOT}', ckan.SITE_ROOT) + this._('Loading...'),
					placement: 'bottom'
				});
				this.el.on('mouseover', this._onMouseOver);
				$(document).on('mouseup', this._onDocumentMouseUp);
				this.sandbox.subscribe('follow-follow-' + this.options.id, this._onHandleFollow);
				this.sandbox.subscribe('follow-unfollow-' + this.options.id, this._onHandleFollow);
			}
		},

		/* Get's called on document click in order to hide popover on not hit
		 *
		 * Returns nothing.
		 */
		_onDocumentMouseUp: function(event) {
			var popover = this.el.data('popover');
			if (typeof popover.$tip != 'undefined') {
				if (popover.$tip.has(event.target).length === 0) {
					this.el.popover('hide');
				}
			}
		},

		/* Helper that changes the loading state of the active popover
		 *
		 * Returns nothing.
		 */
		loadingHelper: function(loading) {
			this.options.loading = loading;
			var popover = this.el.data('popover');
			if (typeof popover.$tip != 'undefined') {
				if (loading) {
					popover.$tip.addClass('popover-context-loading');
				} else {
					popover.$tip.removeClass('popover-context-loading');
				}
			}
		},

		/* Handles the showing of the popover on hover (also hides other active
		 * popovers)
		 *
		 * Returns nothing.
		 */
		_onMouseOver: function() {
			$('[data-module="popover-context"]').popover('hide');
			this.el.popover('show');
			this.getData();
		},

		/* Get's the data from the ckan api
		 *
		 * Returns nothing.
		 */
		getData: function() {
			if (!this.options.loading) {
				this.loadingHelper(true);
				var id = this.options.id;
				var type = this.options.type;
				if (typeof window.popover_context.dict[type][id] == 'undefined') {
					var client = this.sandbox.client;
					var endpoint = type + '_show';
					if (type == 'dataset') {
						endpoint = 'package_show';
					}
					client.call('GET', endpoint, '?id=' + id, this._onHandleData, this._onHandleError);
				} else {
					this._onHandleData(window.popover_context.dict[type][id]);
				}
			}
		},

		/* Handle's a error on the call api
		 *
		 * Returns nothing.
		 */
		_onHandleError: function(error) {
			$('[data-module="popover-context"][data-module-type="'+this.options.type+'"][data-module-id="'+this.options.id+'"]').popover('destroy');
		},

		/* Callback from getting the endpoint from the ckan api
		 *
		 * Returns nothing.
		 */
		_onHandleData: function(json) {
			if (json.success) {
				var id = this.options.id;
				var type = this.options.type;
				var client = this.sandbox.client;
				// set the dictionary
				window.popover_context.dict[type][id] = json;

				// has this been rendered before?
				if (typeof window.popover_context.render[type][id] == 'undefined') {
					var params = this.sanitiseParams(json.result);
					client.getTemplate('popover_context_' + type + '.html', params, this._onRenderPopover);
				} else {
				 	this._onRenderPopover(window.popover_context.render[type][id]);
				}
			}
		},

		/* Used to break down a raw object into something a little more
		 * passable into a GET request
		 *
		 * Returns object.
		 */
		sanitiseParams: function(raw) {
			var type = this.options.type;
			var params = {};
			if (type == 'user') {
				params.id = raw.id;
				params.name = raw.name;
				params.about = raw.about;
				params.display_name = raw.display_name;
				params.num_followers = raw.num_followers;
				params.number_administered_packages = raw.number_administered_packages;
				params.is_me = ( raw.id == this.options.authed );
			} else if (type == 'dataset') {
				params.id = raw.id;
				params.title = raw.title;
				params.name = raw.name;
				params.notes = raw.notes;
				params.num_resources = raw.num_resources;
				params.num_tags = raw.num_tags;
			} else if (type == 'group') {
				params.id = raw.id;
				params.title = raw.title;
				params.name = raw.name;
				params.description = raw.description;
				params.package_count = raw.package_count;
				params.num_followers = raw.num_followers;
			}
			return params;
		},

		/* Renders the contents of the popover
		 *
		 * Returns nothing.
		 */
		_onRenderPopover: function(html) {
			var id = this.options.id;
			var type = this.options.type;
			var dict = window.popover_context.dict[type][id].result;
			var popover = this.el.data('popover');
			if (typeof popover.$tip != 'undefined') {
				var tip	= popover.$tip;
				var title = ( type == 'user' ) ? dict.display_name : dict.title;
				$('.popover-title', tip).html('<a href="javascript:;" class="popover-close">&times;</a>' + title);
				$('.popover-content', tip).html(html);
				$('.popover-close', tip).on('click', this._onClickPopoverClose);
				var follow_check = this.getFollowButton();
				if (follow_check) {
					ckan.module.initializeElement(follow_check[0]);
				}
				this.loadingHelper(false);
			}
			// set the global
			window.popover_context.render[type][id] = html;
		},

		/* Handles closing the currently open popover
		 *
		 * Returns nothing.
		 */
		_onClickPopoverClose: function() {
			this.el.popover('hide');
		},

		/* Handles getting the follow button form within a popover
		 *
		 * Returns jQuery collection || false.
		 */
		getFollowButton: function() {
			var popover = this.el.data('popover');
			if (typeof popover.$tip != 'undefined') {
				var button = $('[data-module="follow"]', popover.$tip);
				if (button.length > 0) {
					return button;
				}
			}
			return false;
		},

		/* Callback from when you follow/unfollow a specified item... this is
		 * used to ensure all popovers associated to that user get re-populated
		 *
		 * Returns nothing.
		 */
		_onHandleFollow: function() {
			delete window.popover_context.render[this.options.type][this.options.id];
		}

	};
});
