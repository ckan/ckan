/**
 * This script is used to add the CSRF token to the HTMX request headers
 * and initializes any ckan modules added to pages via HTMX.
 *
 * Needs to be loaded after htmx
 *
 */
var csrf_field = $('meta[name=csrf_field_name]').attr('content');
var csrf_token = $('meta[name='+ csrf_field +']').attr('content');

htmx.on('htmx:configRequest', (event) => {
  if (csrf_token) {
    event.detail.headers['x-csrftoken'] = csrf_token;
  }
});

function htmx_cleanup_before_swap(event) {
  // Dispose any active tooltips before HTMX swaps the DOM
  event.detail.target.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(
      el => {
    const tooltip = bootstrap.Tooltip.getInstance(el)
    if (tooltip) {
      tooltip.dispose()
    }
  })
}
document.body.addEventListener("htmx:beforeSwap", htmx_cleanup_before_swap);
document.body.addEventListener("htmx:oobBeforeSwap", htmx_cleanup_before_swap);

function htmx_initialize_ckan_modules(event) {
  var elements = event.detail.target.querySelectorAll("[data-module]");

  for (let node of elements) {
    if (node.getAttribute("dm-initialized")) {
      continue;
    }

    ckan.module.initializeElement(node);
    node.setAttribute("dm-initialized", true)
  }

  event.detail.target.querySelectorAll('[data-bs-toggle="tooltip"]'
      ).forEach(node => {
    bootstrap.Tooltip.getOrCreateInstance(node)
  })
}
document.body.addEventListener("htmx:afterSwap", htmx_initialize_ckan_modules);
document.body.addEventListener("htmx:oobAfterSwap", htmx_initialize_ckan_modules);

document.body.addEventListener("htmx:responseError", function(event) {
  const xhr = event.detail.xhr
  const error = $(xhr.response).find('#error-content')
  const headerHTML = error.find('h1').remove().html() || `${xhr.status} ${xhr.statusText}`
  const messageHTML = error.html() || event.detail.error
  $('#responseErrorToast').remove()
  $(`
    <div class="position-fixed bottom-0 end-0 p-3" style="z-index: 11">
      <div id="responseErrorToast" class="toast hide" role="alert" aria-live="assertive" aria-atomic="true">
        <div class="toast-header">
          <strong class="me-auto text-danger">${headerHTML}</strong>
          <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="${ckan.i18n._("Close")}"></button>
        </div>
        <div class="toast-body">
          ${messageHTML}
        </div>
      </div>
    </div>
  `).appendTo('body')
  $('#responseErrorToast').toast('show')
})
