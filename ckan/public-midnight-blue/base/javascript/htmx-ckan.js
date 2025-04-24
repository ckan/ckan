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
  let xhr = event.detail.xhr
  let url = URL.createObjectURL(new Blob([xhr.response]))
  let modal = $(`
    <div class="modal fade">
      <div class="modal-dialog modal-fullscreen">
        <div class="modal-content">
          <div class="modal-header">
            <h3 class="modal-title">${xhr.status} ${xhr.statusText}</h3>
            <button type="button" class="btn-close" data-bs-dismiss="modal"
              aria-label="${ckan.i18n._("Close")}"></button>
          </div>
        <div class="modal-body">
          <iframe style="width:100%; height:100%;" src="${url}"></iframe>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary btn-cancel" data-bs-dismiss="modal"
            >${ckan.i18n._("Close")}</button>
        </div>
      </div>
    </div>`
  )
  modal.modal('show')
})
