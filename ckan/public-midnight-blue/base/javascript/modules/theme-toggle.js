/* Toggles the midnight-blue theme between light and dark mode.
 *
 * Sets/clears `data-theme="dark"` on the <html> element and remembers the
 * choice in localStorage so it persists across page loads. The initial
 * theme (based on the stored preference, falling back to the OS-level
 * `prefers-color-scheme`) is applied by an inline script in
 * templates-midnight-blue/base.html, before this module runs, to avoid a
 * flash of the wrong theme.
 */
ckan.module('theme-toggle', function (jQuery) {
  var STORAGE_KEY = 'ckan.theme-mode';

  return {
    initialize: function () {
      jQuery.proxyAll(this, /_on/);
      this.el.on('click', this._onClick);
      this._render(this._isDark());
    },

    _isDark: function () {
      return document.documentElement.getAttribute('data-theme') === 'dark';
    },

    _onClick: function (event) {
      event.preventDefault();

      var dark = !this._isDark();

      document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');

      try {
        localStorage.setItem(STORAGE_KEY, dark ? 'dark' : 'light');
      } catch (e) {}

      this._render(dark);
    },

    _render: function (dark) {
      this.el.attr('aria-pressed', dark ? 'true' : 'false');

      var label = dark ? this._('Switch to light theme') : this._('Switch to dark theme');
      this.el.attr('aria-label', label);
      this.el.attr('data-bs-original-title', label);

      this.el.find('[data-icon]')
        .toggleClass('fa-moon', !dark)
        .toggleClass('fa-sun', dark);
    }
  };
});
