/* Follow buttons
 * Handles calling the API to follow the current user
 *
 * action - This being the action that the button should perform. Currently: "follow" or "unfollow"
 * type - The being the type of object the user is trying to support. Currently: "user" or "group"
 * id - id of the objec the user is trying to follow
 * loading - State management helper
 *
 * Examples
 *
 *   <a data-module="follow" data-module-action="follow" data-module-type="user" data-module-id="{user_id}">Follow User</a>
 *
 */
this.ckan.module('follow', function($, _) {
	return {
		/* options object can be extended using data-module-* attributes */
		options : {
			action: null,
			type: null,
			id: null,
			loading: false,
			i18n: {
				follow: _('Follow'),
				unfollow: _('Unfollow')
			}
		},

		/* Initialises the module setting up elements and event listeners.
		 *
		 * Returns nothing.
		 */
		initialize: function () {
			$.proxyAll(this, /_on/);
			this.el.on('click', this._onClick);
		},

		/* Handles the clicking of the follow button
		 *
		 * event - An event object.
		 *
		 * Returns nothing.
		 */
		_onClick: function(event) {
			var options = this.options;
			if (
				options.action
				&& options.type
				&& options.id
				&& !options.loading
			) {
				event.preventDefault();
				var client = this.sandbox.client;
				var path = options.action + '_' + options.type;
				options.loading = true;
				this.el.addClass('disabled');
				client.call('POST', path, { id : options.id }, this._onClickLoaded);
			}
		},

		/* Fired after the call to the API to either follow or unfollow
		 *
		 * json - The return json from the follow / unfollow API call
		 *
		 * Returns nothing.
		 */
		_onClickLoaded: function(json) {
			var options = this.options;
			var sandbox = this.sandbox;
			options.loading = false;
			this.el.removeClass('disabled');
			if (options.action == 'follow') {
				options.action = 'unfollow';
				this.el.html('<i class="icon-remove-sign"></i> ' + this.i18n('unfollow')).removeClass('btn-success').addClass('btn-danger');
			} else {
				options.action = 'follow';
				this.el.html('<i class="icon-plus-sign"></i> ' + this.i18n('follow')).removeClass('btn-danger').addClass('btn-success');
			}
			sandbox.publish('follow-' + options.action + '-' + options.id);
		}
	};
});
