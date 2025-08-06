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

document.body.addEventListener("htmx:afterSwap", function (event) {
  htmx_initialize_ckan_modules(event);

  const element = event.detail.requestConfig?.elt;
  if (!element) return;

  const toastHandler = new ToastHandler(element);

  if (event.detail.successful) {
    toastHandler.showToast();
  }
});

class ToastHandler {
  constructor(element, options = {}) {
    this.defaultToastOptions = {
      type: "success",
      title: ckan.i18n._("Notification"),
    };
    this.toastAttributePrefix = options.toastAttributePrefix || "hx-toast-";
    this.options = this.buildToastOptions(element);
  }

  buildToastOptions(element) {
    const options = {};

    for (const attr of element.attributes) {
      if (attr.name.startsWith(this.toastAttributePrefix)) {
        const key = this.convertAttributeNameToKey(attr.name);
        const value = this.parseAttributeValue(attr.value);
        options[key] = value;
      }
    }

    return { ...this.defaultToastOptions, ...options };
  }

  convertAttributeNameToKey(attributeName) {
    return attributeName
      .replace(this.toastAttributePrefix, "")
      .replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
  }

  parseAttributeValue(value) {
    if (['true', 'yes', 't', 'y', '1'].includes(value.toLowerCase())) return true;
    if (['false', 'no', 'f', 'n', '0'].includes(value.toLowerCase())) return false;
    if (!isNaN(value) && value.trim() !== "") return Number(value);
    return value;
  }

  showToast() {
    if (!this.options.message) return;
    ckan.toast(this.options);
  }
}

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

document.addEventListener("htmx:confirm", function (e) {
  // The event is triggered on every trigger for a request, so we need to check if the element
  // that triggered the request has a confirm question set via the hx-confirm attribute,
  // if not we can return early and let the default behavior happen
  if (!e.detail.question) return

  // This will prevent the request from being issued to later manually issue it
  e.preventDefault()

  ckan.confirm({
    message: e.detail.question,
    type: "primary",
    centered: true,
    onConfirm: () => {
      // If the user confirms, we manually issue the request
      // true to skip the built-in window.confirm()
      e.detail.issueRequest(true);
    }
  });
})
