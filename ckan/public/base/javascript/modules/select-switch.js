/* Finds the nearest select box in a form and watches it for changes. When
 * a change occurs it submits the form. It can also hide the submit button if
 * required.
 *
 * target - A selector to watch for changes (default: select)
 * button - A selector for the button to hide in the form.
 *
 * Examples
 *
 *   <form data-module="select-switch" data-module-target="">
 *    <label for="field-order">Sort By:</label>
 *    <select id="field-order"></select>
 *    <button type="submit">Go</button>
 *   </form>
 *
 * Returns .
 */
this.ckan.module('select-switch', function (sandbox, options) {
  sandbox.el.on('change', options.target, function () {
    sandbox.el.submit();
  });

  if (options.button) {
    sandbox.$(options.button).hide();
  }
}, {
  target: 'select',
  button: '[type=submit]'
});
