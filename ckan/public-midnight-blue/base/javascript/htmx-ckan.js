/**
 * This script is used to add the CSRF token to the HTMX request headers
 * and initializes any ckan modules added to pages via HTMX.
 *
 * Needs to be loaded after htmx
 *
 */
var csrf_field = $('meta[name=csrf_field_name]').attr('content');
var csrf_token = $('meta[name=' + csrf_field + ']').attr('content');

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
  event.detail.target.querySelectorAll('.show-filters').forEach(node => {
    node.onclick = function () {
      $("body").addClass("filters-modal")
    }
  })
  event.detail.target.querySelectorAll('.hide-filters').forEach(node => {
    node.onclick = function () {
      $("body").removeClass("filters-modal")
    }
  })
}
document.body.addEventListener("htmx:afterSwap", htmx_initialize_ckan_modules);
document.body.addEventListener("htmx:oobAfterSwap", htmx_initialize_ckan_modules);

document.body.addEventListener("htmx:responseError", function (event) {
  const xhr = event.detail.xhr;

  if (xhr.response.startsWith("<!doctype html>")) {
    const error = $(xhr.response).find('#error-content');
    var message = error.html() || event.detail.error;
  } else {
    var message = xhr.responseText;
  }

  ckan.toast({
    message: message.trim().replace(/^"(.*)"$/, '$1'),
    type: "danger",
    title: `${xhr.status} ${xhr.statusText}`
  });
})
