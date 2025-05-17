/**
 * This script is used to add the CSRF token to the HTMX request headers
 * and initializes any ckan modules added to pages via HTMX.
 *
 * Load this after HTMX and the CSRF module.
 *
 */
htmx.on('htmx:configRequest', function (event) {
  const method = event.detail.verb;

  if (!ckan.csrfSafeMethod(method)) {
    // deferredRequest is critically important to work in async mode
    event.detail.deferredRequest = ckan.fetchCsrfToken().then(csrf => {
      if (csrf) {
        event.detail.headers[csrf.header] = csrf.token;
      }
    });
  }
});


function htmx_initialize_ckan_modules(event) {
  /* ignore swap=none and swap=delete events */
  if (!event.detail.shouldSwap) {
    return;
  }
  var elements = event.detail.target.querySelectorAll("[data-module]");

  for (let node of elements) {
    if (node.getAttribute("dm-initialized")) {
      continue;
    }

    ckan.module.initializeElement(node);
    node.setAttribute("dm-initialized", true)
  }
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
