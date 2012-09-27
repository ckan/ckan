this.ckan.module('follow', function($, _) {
	return {
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
		initialize: function () {
			$.proxyAll(this, /_on/);
			this.el.on('click', this._onClick);
		},
		_onClick: function(e) {
			var options = this.options;
			e.preventDefault();
			if (
				options.action
				&& options.type
				&& options.id
				&& !options.loading
			) {
				var client = this.sandbox.client;
				var path = options.action + '_' + options.type;
				var data = JSON.stringify({ id : options.id });
				options.loading = true;
				this.el.addClass('disabled');
				client.action(path, data, this._onClickLoaded);
			}
			return false;
		},
		_onClickLoaded: function(json) {
			var options = this.options;
			options.loading = false;
			this.el.removeClass('disabled');
			if (options.action == 'follow') {
				options.action = 'unfollow';
				this.el.html('<i class="icon-remove-sign"></i> ' + this.i18n('unfollow')).removeClass('btn-success').addClass('btn-danger');
			} else {
				options.action = 'follow';
				this.el.html('<i class="icon-plus-sign"></i> ' + this.i18n('follow')).removeClass('btn-danger').addClass('btn-success');
			}
		}
	};
});
