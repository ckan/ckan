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
  /* copy error content from response into an alert flash message
     so that the user can see it */
  let message = $(event.detail.xhr.response).find('#error-content')
  message.removeAttr('id').removeAttr('class')
  let alrt = $('<div class="alert alert-danger">').append(message)
  $('#content .flash-messages').append(alrt)[0].scrollIntoView()
})
