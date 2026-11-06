(function (ckan) {

  // Modal that is fading out and is about to be removed from the DOM
  let closingEl = null;

  /**
   * Displays a Bootstrap 5 confirmation modal window
   *
   * Usage:
   *
   * ckan.confirm({
   *    message: "Are you sure you want to delete this item?",
   *    title: "Confirm Deletion",
   *    confirmText: "Yes, Delete",
   *    cancelText: "Cancel",
   *    icon: "<i class='fa fa-trash me-2'></i>",
   *    type: "danger",
   *    onConfirm: function () {
   *      console.log("User confirmed.");
   *    },
   *    onCancel: function () {
   *      console.log("User cancelled.");
   *    }
   * });
   *
   * Options:
   * - message     (string)  [required] Message shown in modal body.
   * - title       (string)  Optional.  Title in modal header.
   * - icon        (string)  Optional.  HTML for icon before title.
   * - confirmText (string)  Optional.  Confirm button label. Default: "Confirm".
   * - cancelText  (string)  Optional.  Cancel button label. Default: "Cancel".
   * - type        (string)  Optional.  Style type ("primary", "danger", etc.).
   * - onConfirm   (func)    Optional.  Called if confirmed.
   * - onCancel    (func)    Optional.  Called if cancelled/closed.
   * - centered    (boolean) Optional.  Whether to center the modal.
   * - scrollable  (boolean) Optional.  Whether to make the modal scrollable.
   * - fullscreen  (boolean) Optional.  Whether to make the modal fullscreen.
   * - backdrop    (boolean | string) Optional.  Backdrop settings.
   * - keyboard    (boolean) Optional.  Whether to close modal on escape.
  */
  var confirm = function (options) {
    if (!options || !options.message) {
      console.error("Confirm: Missing required 'message' option.");
      return;
    }

    const opts = {
      message: options.message,
      title: options.title || ckan.i18n._("Please Confirm"),
      icon: options.icon || "",
      confirmText: options.confirmText || ckan.i18n._("Confirm"),
      cancelText: options.cancelText || ckan.i18n._("Cancel"),
      type: options.type || "default",
      onConfirm: options.onConfirm || function () { },
      onCancel: options.onCancel || function () { },
      centered: options.centered ?? false,
      scrollable: options.scrollable ?? true,
      fullscreen: options.fullscreen ?? false,
      backdrop: options.backdrop ?? "static",
      keyboard: options.keyboard ?? false,
    };

    const style = confirm.styles[opts.type] || confirm.styles.default;
    const select = confirm.selectors;
    const titleId = `${select.modal.slice(1)}-title`;

    const existingEl = document.querySelector(select.modal);

    if (existingEl) {
      if (existingEl !== closingEl) {
        return console.error("Confirm: Modal already exists.");
      }

      // Previous modal is still fading out (e.g. confirm called from its
      // callback), so wait until it's gone
      existingEl.addEventListener("hidden.bs.modal", () => confirm(options), { once: true });
      return;
    }

    const modalHTML = `
      <div class="modal fade" id="${select.modal.slice(1)}" tabindex="-1" aria-labelledby="${titleId}" aria-hidden="true">
        <div class="modal-dialog ${opts.centered ? 'modal-dialog-centered' : ''} ${opts.scrollable ? 'modal-dialog-scrollable' : ''} ${opts.fullscreen ? 'modal-fullscreen' : ''}">
          <div class="modal-content">
            <div class="modal-header ${style.main}">
              ${opts.icon}
              <h3 class="modal-title" id="${titleId}">${opts.title}</h3>
              <button type="button" class="btn-close ${style.btnClose}" aria-label="Close"></button>
            </div>
            <div class="modal-body">${opts.message}</div>
            <div class="modal-footer">
              <button type="button" class="btn btn-secondary btn-cancel" id="${select.cancelBtn.slice(1)}">${opts.cancelText}</button>
              <button type="button" class="btn ${style.confirm}" id="${select.confirmBtn.slice(1)}">${opts.confirmText}</button>
            </div>
          </div>
        </div>
      </div>
    `;

    document.body.insertAdjacentHTML("beforeend", modalHTML);

    const modalEl = document.getElementById(select.modal.slice(1));
    const modal = new bootstrap.Modal(modalEl, {
      backdrop: opts.backdrop, keyboard: opts.keyboard
    });

    const previouslyFocused = document.activeElement;
    let shown = false;
    let settled = false;

    // Bootstrap ignores hide() while the modal is still fading in
    const hide = () => {
      if (shown) {
        return modal.hide();
      }

      modalEl.addEventListener("shown.bs.modal", () => modal.hide(), { once: true });
    };

    // Closes the modal and runs the callback, only once per modal
    const settle = (callback, hiding) => {
      if (settled) {
        return;
      }

      settled = true;
      closingEl = modalEl;

      if (!hiding) {
        hide();
      }

      callback();
    };

    modalEl.addEventListener("shown.bs.modal", () => {
      shown = true;
    });

    modal.show();

    modalEl.addEventListener("hide.bs.modal", () => {
      // Bootstrap sets aria-hidden on the modal once it's hidden, so focus
      // must leave it first
      if (modalEl.contains(document.activeElement)) {
        document.activeElement.blur();
      }

      // Closed with escape or a backdrop click
      settle(opts.onCancel, true);
    });

    // Confirm button click
    document.querySelector(select.confirmBtn)?.addEventListener("click", () => {
      settle(opts.onConfirm);
    });

    // Cancel button or close
    document.querySelectorAll(`${select.cancelBtn}, ${select.modal} ${select.closeBtn}`)
      .forEach(el => {
        el.addEventListener("click", () => {
          settle(opts.onCancel);
        });
      });

    // Cleanup after modal hidden
    modalEl.addEventListener("hidden.bs.modal", () => {
      modal.dispose();
      modalEl.remove();
      closingEl = null;

      if (previouslyFocused?.isConnected) {
        previouslyFocused.focus();
      }
    });
  };

  // Style presets
  confirm.styles = {
    secondary: { btnClose: "btn-close-white", main: "bg-secondary text-white", confirm: "btn-secondary" },
    light: { btnClose: "", main: "bg-light text-dark", confirm: "btn-light" },
    dark: { btnClose: "btn-close-white", main: "bg-dark text-white", confirm: "btn-dark" },
    info: { btnClose: "btn-close-white", main: "bg-info text-white", confirm: "btn-info" },
    primary: { btnClose: "btn-close-white", main: "bg-primary text-white", confirm: "btn-primary" },
    success: { btnClose: "btn-close-white", main: "bg-success text-white", confirm: "btn-success" },
    warning: { btnClose: "btn-close-white", main: "bg-warning text-dark", confirm: "btn-warning" },
    danger: { btnClose: "btn-close-white", main: "bg-danger text-white", confirm: "btn-danger" },
    default: { btnClose: "", main: "", confirm: "btn-primary" }
  };

  confirm.selectors = {
    modal: "#ckan-confirm-modal",
    confirmBtn: "#ckan-confirm-yes",
    cancelBtn: "#ckan-confirm-cancel",
    closeBtn: ".btn-close",
  };

  // Add to ckan namespace
  ckan.sandbox && ckan.sandbox.extend({ confirm: confirm });
  ckan.confirm = confirm;

})(this.ckan);
