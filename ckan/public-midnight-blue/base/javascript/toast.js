(function (ckan, $) {

  /**
   * Displays Bootstrap 5 toast notifications across CKAN
   *
   * Usage:
   *
   * ckan.toast({
   *    message: "Operation completed successfully",
   *    type: "success",
   *    title: "Done",
   *    icon: "<i class='fa fa-check-circle me-2'></i>",
   *    subtitle: "Just now",
   *    delay: 5000,
   *    position: "bottom-right"
   *    stacking: false
   * });
   *
   *
   * Options:
   * - message   (string)  [required] The main message body of the toast.
   * - type      (string)  Optional.  Defines toast style, matches keys from `styles`. Default: "default".
   * - title     (string)  Optional.  Text shown in the toast header.
   * - icon      (string)  Optional.  HTML for an icon displayed before the title.
   * - subtitle  (string)  Optional.  Text shown in the header's small subtitle area.
   * - delay     (number)  Optional.  Time in milliseconds before auto-hide. Default: 3000.
   * - position  (string)  Optional.  Position key controlling toast placement. Default: "bottom-right".
   * - stacking  (boolean) Optional.  Whether to stack toasts on top of each other. Default: true.
  */
  var toast = function (options) {
    if (!options || !options.message) {
      console.error("Toast: Missing required 'message' option.");
      return;
    }

    const opts = {
      type: "default",
      title: "",
      icon: "",
      subtitle: "",
      delay: 3000,
      position: "bottom-right",
      showProgress: true,
      stacking: true,
      ...options
    };

    const style = toast.styles[opts.type] || toast.styles.default;
    const containerEl = toast._createToastContainer(opts);
    const toastEl = document.createElement("div");
    const toastID = `toast-${++toast.count}`;

    toastEl.setAttribute("id", toastID);
    toastEl.setAttribute("role", "alert");
    toastEl.setAttribute("aria-live", "assertive");
    toastEl.setAttribute("aria-atomic", "true");
    toastEl.classList.add("toast", "align-items-center");
    style.border && toastEl.classList.add(style.border);

    toastEl.innerHTML = `
            <div class="toast-header ${style.main}">
                ${opts.icon}
                <strong class="me-auto">${opts.title}</strong>
                <small>${opts.subtitle}</small>
                <button type="button" class="btn-close ${style.btnClose}" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body position-relative">${opts.message}</div>
        `;

    if (!opts.stacking) {
      containerEl.querySelectorAll(".toast").forEach(el => el.remove());
    }

    containerEl.appendChild(toastEl);

    toastEl.addEventListener("hidden.bs.toast", (e) => e.target.remove());

    const hasDelay = typeof opts.delay === "number" && opts.delay > 0;
    const toastInstance = new bootstrap.Toast(toastEl, {
      autohide: hasDelay,
      delay: hasDelay ? opts.delay : 0
    });

    if (hasDelay && opts.showProgress) {
      const progressEl = toast._createProgressBar(opts, style);

      // reset progress bar to 100% on mouse enter
      toastEl.addEventListener("mouseenter", function () {
        progressEl.style.animation = "none";
        progressEl.style.width = "100%";
      });

      // restart progress bar animation on mouse leave
      toastEl.addEventListener("mouseleave", function () {
        progressEl.style.animation = `reverseProgress ${opts.delay / 1000}s linear forwards`;
      });

      toastEl.querySelector(".toast-body").appendChild(progressEl);
    }

    toastInstance.show();
  };

  // count is used to generate unique toast IDs
  toast.count = 0;

  // options are used to configure the toast container and its styles
  toast.options = {
    toastContainer: "toast-container",
    positions: {
      'top-left': 'top-0 start-0 ms-1 mt-1',
      'top-center': 'top-0 start-50 translate-middle-x mt-1',
      'top-right': 'top-0 end-0 me-1 mt-1',
      'middle-left': 'top-50 start-0 translate-middle-y ms-1',
      'middle-center': 'top-50 start-50 translate-middle p-3',
      'middle-right': 'top-50 end-0 translate-middle-y me-1',
      'bottom-left': 'bottom-0 start-0 ms-1 mb-1',
      'bottom-center': 'bottom-0 start-50 translate-middle-x mb-1',
      'bottom-right': 'bottom-0 end-0 me-1 mb-1'
    }
  };

  // styles are used to configure the look of the toast element
  toast.styles = {
    secondary: { btnClose: "btn-close-white", main: "text-white bg-secondary", border: "border-secondary", progress: "bg-secondary" },
    light: { btnClose: "", main: "text-dark bg-light border-bottom border-dark", border: "border-dark", progress: "bg-dark" },
    white: { btnClose: "", main: "text-dark bg-white border-bottom border-dark", border: "border-dark", progress: "bg-dark" },
    dark: { btnClose: "btn-close-white", main: "text-white bg-dark", border: "border-dark", progress: "bg-dark" },
    info: { btnClose: "btn-close-white", main: "text-white bg-info", border: "border-info", progress: "bg-info" },
    primary: { btnClose: "btn-close-white", main: "text-white bg-primary", border: "border-primary", progress: "bg-primary" },
    success: { btnClose: "btn-close-white", main: "text-white bg-success", border: "border-success", progress: "bg-success" },
    warning: { btnClose: "btn-close-white", main: "text-white bg-warning", border: "border-warning", progress: "bg-warning" },
    danger: { btnClose: "btn-close-white", main: "text-white bg-danger", border: "border-danger", progress: "bg-danger" },
    default: { btnClose: "", main: "", border: "", progress: "bg-primary" }
  };

  /**
   * Creates a toast container element and adds it to the DOM
   *
   * There might be multiple toast containers on the page, one for each position
   *
   * @param {Object} opts - toast options
   *
   * @returns {HTMLElement} - the toast container element
  */
  toast._createToastContainer = function (opts) {
    const position = opts.position;
    const containerID = `${toast.options.toastContainer}-${position}`;
    const container = document.getElementById(containerID);

    if (container) return container;

    const wrapper = document.createElement("div");
    const positionClasses = toast.options.positions[position] || toast.options.positions["bottom-right"];

    wrapper.classList.add("position-relative");
    wrapper.setAttribute("role", opts.style === "danger" ? "alert" : "status");
    wrapper.setAttribute("aria-live", opts.style === "danger" ? "assertive" : "polite");
    wrapper.setAttribute("aria-atomic", "true");

    wrapper.innerHTML = `<div id="${containerID}" class="toast-container position-fixed pb-1 ${positionClasses}"></div>`;
    document.body.appendChild(wrapper);

    return document.getElementById(containerID);
  };

  /**
   * Creates a toast progress bar element
   *
   * @param {Object} opts - toast options
   * @param {Object} style - toast style
   *
   * @returns {HTMLElement} - the progress bar element
  */
  toast._createProgressBar = function (opts, style) {
    const progressEl = document.createElement("div");

    progressEl.classList.add("progress-bar-timer", "position-absolute", "bottom-0", "start-0");
    progressEl.classList.add(style.progress)

    progressEl.style.height = "3px";
    progressEl.style.borderBottomLeftRadius = "0.25rem";
    progressEl.style.animation = `reverseProgress ${opts.delay / 1000}s linear forwards`;

    return progressEl;
  };

  // add the toast function to the sandbox and ckan namespace
  ckan.sandbox && ckan.sandbox.extend({ toast: toast });
  ckan.toast = toast;

})(this.ckan, this.jQuery);
